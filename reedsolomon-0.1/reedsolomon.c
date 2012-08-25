/*
 * reedsolomon Python extension module, Copyright 2005 Shane Hathaway.
 * Uses the Reed-Solomon library by Phil Karn.
 *
 * http://hathawaymix.org/Software/ReedSolomon
 * http://www.ka9q.net/code/fec/
 *
 * May be used under the terms of the GNU General Public License (GPL)
 * version 2.
 */

#include "Python.h"
#include "structmember.h"
#include "rs.h"


/*
 * Default parameters by symbol size
 */
struct {
    int gfpoly;
    int fcr;
    int prim;
} default_rs_parameters[] = {
    /*  0 */ {     -1,  -1, -1},
    /*  1 */ {     -1,  -1, -1},
    /*  2 */ {    0x7,   1,  1},
    /*  3 */ {    0xb,   1,  1},
    /*  4 */ {   0x13,   1,  1},
    /*  5 */ {   0x25,   1,  1},
    /*  6 */ {   0x43,   1,  1},
    /*  7 */ {   0x89,   1,  1},
    /*  8 */ {  0x187, 112, 11}, /* Based on CCSDS codec */
    /*  9 */ {  0x211,   1,  1},
    /* 10 */ {  0x409,   1,  1},
    /* 11 */ {  0x805,   1,  1},
    /* 12 */ { 0x1053,   1,  1},
    /* 13 */ { 0x201b,   1,  1},
    /* 14 */ { 0x4443,   1,  1},
    /* 15 */ { 0x8003,   1,  1},
    /* 16 */ {0x1100b,   1,  1},
};

#define DEFAULT_RS_PARAM_COUNT 17


typedef struct {
    PyObject_HEAD
    void (*char_encode)(void *codec,
                        unsigned char *data,
                        unsigned char *parity);
    int (*char_decode)(void *codec,
                       unsigned char *data,
                       int *eras_pos,
                       int no_eras);
    /*
     * rs is non-NULL for GENERAL_CHAR and integer function pairs, but
     * NULL for the CHAR and CCSDS function pairs.
     */
    void *rs;
    int integertype;
    int n;  /* data symbols + parity symbols */
    int k;  /* data symbols */
    int symsize, gfpoly, fcr, prim, nroots, pad;
    int mask;  /* bits not allowed in symbols */
    char variant[10];
} Codec;


/*
 * librs provides three function pairs for working with characters:
 * 8-bit symbols, CCSDS-compatible 8-bit symbols, and character symbols
 * with a variable number of bits.  The functions below call the
 * library.
 */

static void
char_encode_CHAR(void *codec, unsigned char *data, unsigned char *parity)
{
    encode_rs_8(data, parity, ((Codec*) codec)->pad);
}

static void
char_encode_CCSDS(void *codec, unsigned char *data, unsigned char *parity)
{
    encode_rs_ccsds(data, parity, ((Codec*) codec)->pad);
}

static void
char_encode_GENERAL_CHAR(void *codec, unsigned char *data,
                         unsigned char *parity)
{
    encode_rs_char(((Codec*) codec)->rs, data, parity);
}

static int
char_decode_CHAR(void *codec, unsigned char *data,
                 int *eras_pos, int no_eras)
{
    return decode_rs_8(data, eras_pos, no_eras, ((Codec*) codec)->pad);
}

static int
char_decode_CCSDS(void *codec, unsigned char *data,
                  int *eras_pos, int no_eras)
{
    return decode_rs_ccsds(data, eras_pos, no_eras, ((Codec*) codec)->pad);
}

static int
char_decode_GENERAL_CHAR(void *codec, unsigned char *data,
                         int *eras_pos, int no_eras)
{
    return decode_rs_char(((Codec*) codec)->rs, data, eras_pos, no_eras);
}


/* Exception type */
PyObject *UncorrectableError;


static void
stringcodec_dealloc(Codec* self)
{
    if (self->rs)
        free_rs_char(self->rs);
}

static void
intcodec_dealloc(Codec* self)
{
    if (self->rs)
        free_rs_int(self->rs);
}

static PyObject *
codec_repr(Codec *self)
{
    return PyString_FromFormat("<%s(n=%d, k=%d, symsize=%d, gfpoly=%d, "
                               "fcr=%d, prim=%d, variant='%s')>",
                               self->integertype ? "IntegerCodec" : "Codec",
                               self->n, self->k, self->symsize,
                               self->gfpoly, self->fcr, self->prim,
                               self->variant);
}


/* Fill unspecified defaults */
static int codec_fill_params(Codec *self) {
    if (self->gfpoly == -1 || self->fcr == -1 || self->prim == -1) {
        /* Apply default codec parameters */
        if (self->symsize < 0 || self->symsize >= DEFAULT_RS_PARAM_COUNT ||
            default_rs_parameters[self->symsize].gfpoly < 0) {
            PyErr_Format(PyExc_ValueError,
                         "No defaults available for symsize=%d",
                         self->symsize);
            return -1;
        }
        if (self->gfpoly == -1)
            self->gfpoly = default_rs_parameters[self->symsize].gfpoly;
        if (self->fcr == -1)
            self->fcr = default_rs_parameters[self->symsize].fcr;
        if (self->prim == -1)
            self->prim = default_rs_parameters[self->symsize].prim;
    }
    self->nroots = self->n - self->k;
    self->pad = (1 << self->symsize) - self->n - 1;
    return 0;
}

#define valuerror_neg(reason) \
  {PyErr_SetString(PyExc_ValueError, (reason)); return -1;}
#define valuerror_null(reason) \
  {PyErr_SetString(PyExc_ValueError, (reason)); return NULL;}

static int
codec_check_params(Codec *self) {
    if (self->symsize <= 0) valuerror_neg("symsize <= 0");
    if (self->integertype) {
        if (self->symsize > 32)
            valuerror_neg("symsize > 32");
    }
    else {
        if (self->symsize > 8)
            valuerror_neg("symsize > 8");
    }
    if (self->n < 2) valuerror_neg("n < 2");
    if (self->n > (1 << self->symsize) - 1)
        valuerror_neg("n > 2 ** symsize - 1");
    /*
     * For string codecs, double-check that n <= 255,
     * avoiding buffer overruns
     */
    if (!self->integertype && self->n > 255)
        valuerror_neg("n > 255");
    
    if (self->k >= self->n) valuerror_neg("k >= n");
    if (self->n != self->k + self->nroots) valuerror_neg("n != k + nroots");
    return 0;
}

static char stringcodec_doc[] = 
"Reed-Solomon string encoder/decoder\n"
"\n"
"Constructor signature:\n"
"Codec(n, k [,symsize [,gfpoly [,fcr [,prim [,variant]]]]])\n"
"\n"
"n is the total number of symbols per codeword, including data\n"
"and parity.  k is the number of data symbols per codeword.\n"
"symsize, which defaults to 8, is the number of bits per symbol.\n"
"In this codec, symsize can not be larger than 8.\n"
"Note that n must be less than 2**symsize.  gfpoly, fcr, and\n"
"prim are parameters for the Reed-Solomon polynomial\n"
"calculations.  If not specified, default values for gfpoly,\n"
"fcr, and prim will be chosen based on symsize.  variant is\n"
"either 'char' or 'ccsds'; the 'ccsds' variant is designed to\n"
"implement the CCSDS encoding standard.\n";

static PyObject*
stringcodec_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    char *variant;
    Codec *self;
    int using_defaults, create_rs;
    static char *kwlist[] = {
        "n", "k", "symsize", "gfpoly", "fcr", "prim", "variant", NULL};

    self = (Codec *)type->tp_alloc(type, 0);
    if (!self)
        return NULL;
    self->integertype = 0;
    self->symsize = 8;
    self->gfpoly = -1;
    self->fcr = -1;
    self->prim = -1;
    variant = "char";

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "ii|iiiis", kwlist,
        &self->n, &self->k, &self->symsize, &self->gfpoly,
        &self->fcr, &self->prim, &variant))
        goto error;
    if (codec_fill_params(self) < 0)
        goto error;

    using_defaults = (self->symsize == 8 &&
                      self->gfpoly == 0x187 &&
                      self->fcr == 112 &&
                      self->prim == 11 &&
                      self->nroots == 32);
    create_rs = 0;
    if (strcmp(variant, "char") == 0) {
        if (using_defaults) {
            self->char_encode = char_encode_CHAR;
            self->char_decode = char_decode_CHAR;
        }
        else {
            create_rs = 1;
            self->char_encode = char_encode_GENERAL_CHAR;
            self->char_decode = char_decode_GENERAL_CHAR;
        }
    }
    else if (strcmp(variant, "ccsds") == 0) {
        self->char_encode = char_encode_CCSDS;
        self->char_decode = char_decode_CCSDS;
        if (!using_defaults) {
            PyErr_SetString(PyExc_ValueError,
                            "Invalid parameters for the 'ccsds' variant");
            goto error;
        }
    }
    else {
        PyErr_Format(PyExc_ValueError, "Variant not recognized: %s", variant);
        goto error;
    }
    strcpy(self->variant, variant);
    if (codec_check_params(self) < 0)
        goto error;

    if (create_rs) {
        self->rs = init_rs_char(self->symsize, self->gfpoly, self->fcr,
                                self->prim, self->nroots, self->pad);
        if (!self->rs) {
            PyErr_NoMemory();
            goto error;
        }
        self->mask = (0xff << self->symsize) & 0xff;
    }
    else {
        self->rs = NULL;
        self->mask = 0;
    }
    return (PyObject *) self;

 error:
    Py_DECREF((PyObject*) self);
    return NULL;
}


static int
stringcodec_checksymbols(Codec *self, unsigned char *data, int datalen) {
    int i, mask;

    mask = self->mask;
    if (mask) {
        /* Sanity-check the input */
        for (i = 0; i < datalen; i++) {
            if (data[i] & mask) {
                PyErr_Format(PyExc_ValueError,
                             "This codec requires symbols to be less than %d",
                             (1 << self->symsize));
                return -1;
            }
        }
    }
    return 0;
}


/*
 * Convert a Python sequence to an array of integers,
 * for use as erasure indexes.
 */
static int*
create_erasure_array(Codec *self, PyObject *erasures, int *no_eras_out,
                     int *array_size_out) {
    PyObject *tmp;
    int no_eras = 0;
    int i, v;
    int *eras_pos = NULL;
    int alloc_eras = self->nroots;
    int array_size;

    if (erasures) {
        no_eras = PySequence_Size(erasures);
        if (no_eras < 0)
            return NULL;
        if (alloc_eras < no_eras)
            alloc_eras = no_eras;
    }
    array_size = sizeof(int) * alloc_eras;
    eras_pos = (int *) PyMem_Malloc(array_size);
    if (!eras_pos)
        return NULL;
    if (erasures) {
        for (i = 0; i < PySequence_Size(erasures); i++) {
            tmp = PySequence_GetItem(erasures, i);
            if (!tmp)
                goto error;
            v = PyInt_AsLong(tmp);
            Py_DECREF(tmp);
            if (v < 0 || v >= self->n) {
                PyErr_Format(PyExc_ValueError,
                             "Erasure indexes must be non-negative "
                             "integers less than %d", self->n);
                goto error;
            }
            /*
             * TODO: It is unclear whether librs expects padded
             * erasure indexes, but version 4.0 appears to expect padding.
             * Verify this was Phil Karn's intent.
             */
            eras_pos[i] = self->pad + v;
        }
    }
    *no_eras_out = no_eras;
    if (array_size_out)
        *array_size_out = array_size;
    return eras_pos;

 error:
    if (eras_pos != NULL)
        PyMem_Free(eras_pos);
    return NULL;
}


static PyObject *
convert_decode_result(Codec *self, PyObject *output, int *eras_pos,
                      int count) {
    PyObject *corrections=NULL, *res, *tmp;
    int i, index;

    corrections = PyList_New(count);
    if (!corrections)
        return NULL;
    for (i = 0; i < count; i++) {
        /*
         * TODO: It is unclear whether librs intends to return padded
         * correction indexes, but version 4.0 returns padded indexes.
         * Verify this was Phil Karn's intent.
         */
        index = eras_pos[i] - self->pad;
        if (index < 0) {
            /*
             * The codec tried to correct a symbol in the pad region.
             * This indicates there were too many errors to correct.
             */
            PyErr_SetString(UncorrectableError, "Corrupted input");
            goto error;
        }
        tmp = PyInt_FromLong(index);
        if (!tmp)
            goto error;
        PyList_SET_ITEM(corrections, i, tmp);
    }
    res = PyTuple_New(2);
    if (!res)
        goto error;
    Py_INCREF(output);
    PyTuple_SET_ITEM(res, 0, output);
    PyTuple_SET_ITEM(res, 1, corrections);
    return res;

 error:
    Py_XDECREF(corrections);
    return NULL;
}


static char stringcodec_encode_doc[] = 
"encode(string) -> encoded_string\n"
"\n"
"Encode a string.  The input string must have self.k characters.\n"
"The encoded string will have self.n characters.\n";

static PyObject *
stringcodec_encode(Codec *self, PyObject *args)
{
    unsigned char *src, *data, *parity;
    int srclen;
    PyObject *output;

    if (!PyArg_ParseTuple(args, "s#", &src, &srclen))
        return NULL;
    if (srclen != self->k) {
        PyErr_Format(PyExc_ValueError,
                     "String to encode must contain exactly %d bytes",
                     self->k);
        return NULL;
    }
    if (stringcodec_checksymbols(self, src, srclen) < 0)
        return NULL;
    if (!(output = PyString_FromStringAndSize(NULL, self->n))) {
        return NULL;
    }
    data = PyString_AS_STRING(output);
    memcpy(data, src, self->k);
    parity = data + self->k;
    self->char_encode(self, data, parity);
    return output;
}


static char stringcodec_decode_doc[] = 
"decode(encoded_string [,erasures]) -> (string, corrections)\n"
"\n"
"Decode a string.  The input string must have self.n characters.\n"
"The optional second argument provides a list of erasure indexes;\n"
"the erasure list must not contain duplicate indexes.\n"
"Returns a 2-tuple containing the decoded string (with self.k\n"
"characters) and a list of indexes of corrections made to the\n"
"input string.\n";

static PyObject *
stringcodec_decode(Codec *self, PyObject *args)
{
    unsigned char *src;
    unsigned char data[256];  /* Sufficient as long as self->n <= 255 */
    PyObject *erasures=NULL, *output=NULL, *res=NULL;
    int no_eras, count, srclen;
    int *eras_pos = NULL;

    if (!PyArg_ParseTuple(args, "s#|O", &src, &srclen, &erasures))
        return NULL;
    if (srclen != self->n) {
        PyErr_Format(PyExc_ValueError,
                     "String to decode must contain exactly %d bytes",
                     self->n);
        return NULL;
    }
    if (stringcodec_checksymbols(self, src, srclen) < 0)
        return NULL;
    if (!(eras_pos = create_erasure_array(self, erasures, &no_eras, NULL)))
        goto error;
    memcpy(data, src, srclen);
    data[self->n] = 0;
    count = self->char_decode(self, data, eras_pos, no_eras);
    if (count < 0) {
        PyErr_SetString(UncorrectableError,
                        "Too many errors or erasures in input");
        goto error;
    }
    output = PyString_FromStringAndSize(data, self->k);
    if (!output)
        goto error;
    res = convert_decode_result(self, output, eras_pos, count);
 error:
    if (eras_pos != NULL)
        PyMem_Free(eras_pos);
    Py_XDECREF(output);
    return res;
}


static char stringcodec_encodechunks_doc[] = 
"encodechunks(chunks) -> encoded_chunks\n"
"\n"
"Encode interleaved chunks.\n"
"All input chunks must have the same size.  The number of input\n"
"chunks must be self.k.  The encoded chunk list will have self.n\n"
"chunks, all having the same length as the input chunks.\n";

static PyObject *
stringcodec_encodechunks(Codec *self, PyObject *args)
{
    int i, j, length, rows = -1;
    PyObject *o, *srcs;
    PyObject *encoded = NULL;
    /* 256 is enough as long as self->n <= 255 */
    char data_str[256], parity_str[256];
    char *inputs[256], *outputs[256];
    int k = self->k, n = self->n, nroots = self->nroots;

    if (!PyArg_ParseTuple(args, "O", &srcs))
        return NULL;
    length = PySequence_Size(srcs);
    if (length < 0) {
        PyErr_SetString(PyExc_TypeError, "Input must be a sequence");
        goto error;
    }
    if (length != k) {
        PyErr_Format(PyExc_ValueError,
                     "Expected %d strings, but got %d strings",
                     k, length);
        goto error;
    }
    encoded = PyTuple_New(n);
    if (!encoded)
        goto error;

    for (i = 0; i < k; i++) {
        o = PySequence_GetItem(srcs, i);
        if (!o)
            goto error;
        PyTuple_SET_ITEM(encoded, i, o);
        length = PyString_Size(o);
        if (length < 0)
            goto error;
        if (rows == -1)
            rows = length;
        else if (rows != length) {
            PyErr_SetString(PyExc_ValueError,
                            "The input strings have unequal length");
            goto error;
        }
        inputs[i] = PyString_AsString(o);
        if (!inputs[i])
            goto error;
        if (stringcodec_checksymbols(self, inputs[i], length) < 0)
            goto error;
    }

    for (i = 0; i < nroots; i++) {
        o = PyString_FromStringAndSize(NULL, rows);
        if (!o)
            goto error;
        PyTuple_SET_ITEM(encoded, k + i, o);
        outputs[i] = PyString_AS_STRING(o);
    }

    /* Do the real work */
    Py_BEGIN_ALLOW_THREADS
    for (i = 0; i < rows; i++) {
        for (j = 0; j < k; j++)
            data_str[j] = inputs[j][i];
        self->char_encode(self, data_str, parity_str);
        for (j = 0; j < nroots; j++)
            outputs[j][i] = parity_str[j];
    }
    Py_END_ALLOW_THREADS
    return encoded;

 error:
    Py_XDECREF(encoded);
    return NULL;
}


static char stringcodec_decodechunks_doc[] = 
"decodechunks(encoded_chunks [,erasures]) -> (chunks, corrections)\n"
"\n"
"Decode interleaved chunks.\n"
"All input chunks must have the same size.  The number of input\n"
"chunks must be self.n.  The decoded chunk list will have self.k\n"
"chunks, all having the same length as the input chunks.  The\n"
"corrections list will contain a union of the indexes of\n"
"corrections made in any code word.\n";

static PyObject *
stringcodec_decodechunks(Codec *self, PyObject *args)
{
    int i, j, index, length, rows = -1;
    int no_eras, eras_array_size, count;
    PyObject *o, *srcs, *erasures=NULL;
    PyObject *encoded = NULL, *decoded = NULL, *corrections = NULL, *res=NULL;
    int *eras_pos = NULL, *const_eras_pos = NULL;
    /* 256 is enough as long as self->n <= 255 */
    char codeword[256], corrected[256];
    char *inputs[256], *outputs[256];
    int k = self->k, n = self->n;
    PyThreadState *_save;

    if (!PyArg_ParseTuple(args, "O|O", &srcs, &erasures))
        return NULL;
    length = PySequence_Size(srcs);
    if (length < 0) {
        PyErr_SetString(PyExc_TypeError, "Input must be a sequence");
        goto error;
    }
    if (length != n) {
        PyErr_Format(PyExc_ValueError,
                     "Expected %d input strings, but got %d strings",
                     n, length);
        goto error;
    }
    encoded = PyTuple_New(n);
    if (!encoded)
        goto error;
    decoded = PyTuple_New(k);
    if (!decoded)
        goto error;

    for (i = 0; i < n; i++) {
        o = PySequence_GetItem(srcs, i);
        if (!o)
            goto error;
        /* Hold references to the encoded strings, just in case the input
           sequence produces strings dynamically. */
        PyTuple_SET_ITEM(encoded, i, o);
        length = PyString_Size(o);
        if (length < 0)
            goto error;
        if (rows == -1)
            rows = length;
        else if (rows != length) {
            PyErr_SetString(PyExc_ValueError,
                            "The input strings have unequal length");
            goto error;
        }
        inputs[i] = PyString_AsString(o);
        if (!inputs[i])
            goto error;
        if (stringcodec_checksymbols(self, inputs[i], length) < 0)
            goto error;
    }

    for (i = 0; i < k; i++) {
        o = PyString_FromStringAndSize(NULL, rows);
        if (!o)
            goto error;
        PyTuple_SET_ITEM(decoded, i, o);
        outputs[i] = PyString_AS_STRING(o);
    }
    
    if (!(const_eras_pos = create_erasure_array(self, erasures, &no_eras,
                                                &eras_array_size)))
        goto error;
    if (!(eras_pos = PyMem_Malloc(eras_array_size)))
        goto error;

    codeword[n] = 0;
    /*
     * corrected is an array of flags indicating whether the
     * corresponding index was corrected.
     */
    memset(corrected, 0, n);

    /* Do the real work */
    Py_UNBLOCK_THREADS
    for (i = 0; i < rows; i++) {
        for (j = 0; j < n; j++)
            codeword[j] = inputs[j][i];
        memcpy(eras_pos, const_eras_pos, eras_array_size);
        count = self->char_decode(self, codeword, eras_pos, no_eras);
        if (count < 0) {
            Py_BLOCK_THREADS
            PyErr_SetString(UncorrectableError,
                            "Too many errors or erasures in input");
            goto error;
        }
        for (j = 0; j < k; j++)
            outputs[j][i] = codeword[j];
        for (j = 0; j < count; j++) {
            index = (eras_pos[j] - self->pad);
            if (index < 0 || index >= n) {
                /* Tried to correct an impossible index */
                Py_BLOCK_THREADS
                PyErr_SetString(UncorrectableError, "Corrupted input");
                goto error;
            }
            corrected[index] = 1;
        }
    }
    Py_BLOCK_THREADS

    /* Construct the return value */
    corrections = PyList_New(0);
    if (!corrections)
        goto error;
    for (i = 0; i < n; i++) {
        if (corrected[i]) {
            o = PyInt_FromLong(i);
            if (!o)
                goto error;
            if (PyList_Append(corrections, o) < 0) {
                Py_DECREF(o);
                goto error;
            }
            Py_DECREF(o);
        }
    }
    res = PyTuple_New(2);
    if (!res)
        goto error;
    Py_INCREF(decoded);
    PyTuple_SET_ITEM(res, 0, decoded);
    Py_INCREF(corrections);
    PyTuple_SET_ITEM(res, 1, corrections);

 error:
    Py_XDECREF(encoded);
    Py_XDECREF(decoded);
    Py_XDECREF(corrections);
    if (eras_pos)
        PyMem_Free(eras_pos);
    if (const_eras_pos)
        PyMem_Free(const_eras_pos);
    return res;
}


static char stringcodec_updatechunk_doc[] = 
"updatechunk(dataindex, datadelta, parityindex, oldparity) -> newparity\n"
"\n"
"Compute a new parity chunk when data chunks have changed.\n"
"dataindex is the index of the data chunk that has changed.\n"
"datadelta is the difference between the old value and the\n"
"new value.  datadelta is a string containing the XOR of the\n"
"old and new data (you can use this module's xor utility.)\n"
"parityindex is the code word index of the parity value to\n"
"compute.  oldparity is the former parity chunk at that index.\n"
"datadelta and oldparity must have the same length.\n";

static PyObject *
stringcodec_updatechunk(Codec *self, PyObject *args)
{
    int dataindex;
    char *datadelta;
    int rows;
    int parityindex;
    char *oldparity;
    int oldparitylen;
    int i;
    /* 256 is enough as long as self->n <= 255 */
    char data_str[256], parity_str[256];
    PyObject *py_newparity = NULL;
    char *newparity;

    if (!PyArg_ParseTuple(args, "is#is#",
                          &dataindex, &datadelta, &rows,
                          &parityindex, &oldparity, &oldparitylen))
        return NULL;
    if (rows != oldparitylen)
        valuerror_null("datadelta and oldparity must have the same length");
    if (parityindex < self->k)
        valuerror_null("parityindex < self.k");
    if (parityindex >= self->n)
        valuerror_null("parityindex >= self.n");
    if (dataindex < 0)
        valuerror_null("dataindex < 0");
    if (dataindex >= self->k)
        valuerror_null("dataindex >= self.k");
    
    py_newparity = PyString_FromStringAndSize(NULL, oldparitylen);
    if (!py_newparity)
        goto error;
    newparity = PyString_AsString(py_newparity);
    if (!newparity)
        goto error;

    /*
     * This takes advantage of two properties of RS coding: Encoding
     * is simple matrix multiplication, and both adding and
     * subtracting are implemented using XOR.  Because of these
     * properties, if you multiply a row delta (computed using XOR) by
     * the standard codec's matrix, you get back a codeword delta,
     * which you can XOR with a part of the old codeword to get part
     * of the correct new codeword.  This might be faster if we used
     * Galois field operations directly, but this method works fine.
     */
    Py_BEGIN_ALLOW_THREADS
    memset(data_str, 0, self->k);
    for (i = 0; i < rows; i++) {
        data_str[dataindex] = datadelta[i];
        self->char_encode(self, data_str, parity_str);
        newparity[i] = oldparity[i] ^ parity_str[parityindex - self->k];
    }
    Py_END_ALLOW_THREADS
    return py_newparity;

 error:
    Py_XDECREF(py_newparity);
    return NULL;
}


static char intcodec_doc[] = 
"Reed-Solomon integer array encoder/decoder\n"
"\n"
"Constructor signature:\n"
"IntegerCodec(n, k [,symsize [,gfpoly [,fcr [,prim]]]])\n"
"\n"
"n is the total number of symbols per codeword, including data\n"
"and parity.  k is the number of data symbols per codeword.\n"
"symsize, which defaults to 8, is the number of bits per symbol.\n"
"In this codec, symsize can be as high as 32, although 32\n"
"bits would cause the codec to build excessively large tables.\n"
"Note that n must be less than 2**symsize.  gfpoly, fcr, and\n"
"prim are parameters for the Reed-Solomon polynomial\n"
"calculations.  If not specified, default values for gfpoly,\n"
"fcr, and prim will be chosen based on symsize.\n";

static PyObject*
intcodec_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    Codec *self;
    static char *kwlist[] = {
        "n", "k", "symsize", "gfpoly", "fcr", "prim", NULL};

    self = (Codec *)type->tp_alloc(type, 0);
    if (!self)
        return NULL;
    self->integertype = 1;
    self->symsize = 8;
    self->gfpoly = -1;
    self->fcr = -1;
    self->prim = -1;
    strcpy(self->variant, "int");
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "ii|iiii", kwlist,
        &self->n, &self->k, &self->symsize, &self->gfpoly,
        &self->fcr, &self->prim))
        goto error;
    if (codec_fill_params(self) < 0)
        goto error;
    if (codec_check_params(self) < 0)
        goto error;

    self->rs = init_rs_int(self->symsize, self->gfpoly, self->fcr,
                           self->prim, self->nroots, self->pad);
    if (!self->rs)
        goto alloc_failed;
    self->mask = (-1) << self->symsize;
    self->char_encode = NULL;
    self->char_decode = NULL;
    return (PyObject*) self;

 alloc_failed:
    PyErr_NoMemory();
 error:
    Py_DECREF((PyObject*) self);
    return NULL;
}


/* Create an array of integer symbols from a Python sequence */
static int*
intcodec_make_array(Codec *self, PyObject *src) {
    PyObject *tmp;
    int *data;
    int srclen, i, v;

    srclen = PySequence_Size(src);
    if (srclen < 0)
        return NULL;
    data = (int *) PyMem_Malloc(sizeof(int) * srclen);
    if (!data)
        return NULL;
    for (i = 0; i < srclen; i++) {
        tmp = PySequence_GetItem(src, i);
        if (!tmp)
            goto error;
        v = PyInt_AsLong(tmp);
        Py_DECREF(tmp);
        if (v & self->mask) {
            PyErr_Format(PyExc_ValueError,
                         "This codec requires symbols to be less than %d",
                         (1 << self->symsize));
            goto error;
        }
        data[i] = v;
    }
    return data;
 error:
    PyMem_Free(data);
    return NULL;
}


static char intcodec_encode_doc[] = 
"encode(sequence) -> encoded_sequence\n"
"\n"
"Encode a sequence of integers.  The input sequence must have self.k\n"
"integer elements.  The output sequence will have self.n elements.\n";

static PyObject *
intcodec_encode(Codec *self, PyObject *args)
{
    PyObject *src, *tmp;
    int *data=NULL, *parity=NULL;
    PyObject *output=NULL;
    int srclen, i;

    if (!PyArg_ParseTuple(args, "O", &src))
        return NULL;
    srclen = PySequence_Size(src);
    if (srclen < 0)
        return NULL;
    if (srclen != self->k) {
        PyErr_Format(PyExc_ValueError,
                     "Sequence to encode must contain exactly %d integers",
                     self->k);
        return NULL;
    }
    data = intcodec_make_array(self, src);
    if (!data)
        goto error;
    parity = (int *) PyMem_Malloc(sizeof(int) * self->nroots);
    if (!parity)
        goto error;
    encode_rs_int(self->rs, data, parity);
    output = PyList_New(self->n);
    if (!output)
        goto error;
    for (i = 0; i < srclen; i++) {
        tmp = PySequence_GetItem(src, i);
        if (!tmp)
            goto error;
        Py_INCREF(tmp);
        PyList_SET_ITEM(output, i, tmp);
    }
    for (i = 0; i < self->nroots; i++) {
        tmp = PyInt_FromLong(parity[i]);
        if (!tmp)
            goto error;
        PyList_SET_ITEM(output, self->k + i, tmp);
    }
    PyMem_Free(data);
    PyMem_Free(parity);
    return output;

 error:
    if (data != NULL)
        PyMem_Free(data);
    if (parity != NULL)
        PyMem_Free(parity);
    Py_XDECREF(output);
    return NULL;
}


static char intcodec_decode_doc[] = 
"decode(encoded_sequence [, erasures]) -> (sequence, corrections)\n"
"\n"
"Decode a sequence of integers.  The input sequence must have self.n\n"
"integer elements. The optional second argument provides a list of\n"
"erasure indexes; the erasure list must not contain duplicate\n"
"indexes.  Returns a 2-tuple containing the decoded list of integers\n"
"(with self.k characters) and a list of indexes of corrections made\n"
"to the input sequence.\n";

static PyObject *
intcodec_decode(Codec *self, PyObject *args)
{
    PyObject *src=NULL, *erasures=NULL, *output=NULL, *res=NULL, *tmp;
    int no_eras, count, srclen, i;
    int *data=NULL, *eras_pos=NULL;

    if (!PyArg_ParseTuple(args, "O|O", &src, &erasures))
        return NULL;
    srclen = PySequence_Size(src);
    if (srclen < 0)
        return NULL;
    if (srclen != self->n) {
        PyErr_Format(PyExc_ValueError,
                     "Sequence to decode must contain exactly %d bytes",
                     self->n);
        return NULL;
    }
    if (!(data = intcodec_make_array(self, src)))
        goto error;
    if (!(eras_pos = create_erasure_array(self, erasures, &no_eras, NULL)))
        goto error;
    count = decode_rs_int(self->rs, data, eras_pos, no_eras);
    if (count < 0) {
        PyErr_SetString(UncorrectableError,
                        "Too many errors or erasures in input");
        goto error;
    }
    output = PyList_New(self->k);
    if (!output)
        goto error;
    for (i = 0; i < self->k; i++) {
        tmp = PyInt_FromLong(data[i]);
        if (!tmp)
            goto error;
        PyList_SET_ITEM(output, i, tmp);
    }
    res = convert_decode_result(self, output, eras_pos, count);
 error:
    if (data != NULL)
        PyMem_Free(data);
    if (eras_pos != NULL)
        PyMem_Free(eras_pos);
    Py_XDECREF(output);
    return res;
}


static char module_xor_doc[] = 
"xor(s1, s2) -> s\n"
"\n"
"Utility function that computes the XOR value of two strings.\n"
"The strings must have equal length.\n";

static PyObject*
module_xor(PyObject *self, PyObject *args)
{
    char *s1, *s2;
    int s1len, s2len;
    PyObject *res;
    char *res_data;

    if (!PyArg_ParseTuple(args, "s#s#", &s1, &s1len, &s2, &s2len))
        return NULL;
    if (s1len != s2len) {
        PyErr_SetString(PyExc_ValueError,
                        "The strings have unequal length");
        return NULL;
    }
    res = PyString_FromStringAndSize(NULL, s1len);
    if (!res)
        return NULL;
    res_data = PyString_AsString(res);
    if (!res_data) {
        Py_DECREF(res);
        return NULL;
    }
    while (s1len) {
        *res_data++ = *s1++ ^ *s2++;
        s1len--;
    }
    return res;
}


static PyMethodDef stringcodec_methods[] = {
    {"encode", (PyCFunction)stringcodec_encode, METH_VARARGS,
     stringcodec_encode_doc},
    {"decode", (PyCFunction)stringcodec_decode, METH_VARARGS,
     stringcodec_decode_doc},
    {"encodechunks", (PyCFunction)stringcodec_encodechunks, METH_VARARGS,
     stringcodec_encodechunks_doc},
    {"decodechunks", (PyCFunction)stringcodec_decodechunks, METH_VARARGS,
     stringcodec_decodechunks_doc},
    {"updatechunk", (PyCFunction)stringcodec_updatechunk, METH_VARARGS,
     stringcodec_updatechunk_doc},
    {NULL}
};

static PyMethodDef intcodec_methods[] = {
    {"encode", (PyCFunction)intcodec_encode, METH_VARARGS,
     intcodec_encode_doc},
    {"decode", (PyCFunction)intcodec_decode, METH_VARARGS,
     intcodec_decode_doc},
    {NULL}
};

static PyMemberDef codec_members[] = {
    {"n", T_INT, offsetof(Codec, n), READONLY},
    {"k", T_INT, offsetof(Codec, k), READONLY},
    {"symsize", T_INT, offsetof(Codec, symsize), READONLY},
    {"gfpoly", T_INT, offsetof(Codec, gfpoly), READONLY},
    {"fcr", T_INT, offsetof(Codec, fcr), READONLY},
    {"prim", T_INT, offsetof(Codec, prim), READONLY},
    {"nroots", T_INT, offsetof(Codec, nroots), READONLY},
    {"pad", T_INT, offsetof(Codec, pad), READONLY},
    {"mask", T_INT, offsetof(Codec, mask), READONLY},
    {"variant", T_STRING_INPLACE, offsetof(Codec, variant), READONLY},
    {NULL}
};

/* List of methods defined in the module */

static struct PyMethodDef module_methods[] = {
    {"xor", (PyCFunction)module_xor, METH_VARARGS, module_xor_doc},
    {NULL}
};

static PyTypeObject CodecType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "reedsolomon.Codec",       /*tp_name*/
    sizeof(Codec), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)stringcodec_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    (reprfunc)codec_repr,      /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,        /*tp_flags*/
    stringcodec_doc,           /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    stringcodec_methods,       /* tp_methods */
    codec_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    0,                         /* tp_init */
    0,                         /* tp_alloc */
    stringcodec_new,             /* tp_new */
};


static PyTypeObject IntegerCodecType = {
    PyObject_HEAD_INIT(NULL)
    0,                         /*ob_size*/
    "reedsolomon.IntegerCodec", /*tp_name*/
    sizeof(Codec), /*tp_basicsize*/
    0,                         /*tp_itemsize*/
    (destructor)intcodec_dealloc, /*tp_dealloc*/
    0,                         /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                         /*tp_compare*/
    (reprfunc)codec_repr,      /*tp_repr*/
    0,                         /*tp_as_number*/
    0,                         /*tp_as_sequence*/
    0,                         /*tp_as_mapping*/
    0,                         /*tp_hash */
    0,                         /*tp_call*/
    0,                         /*tp_str*/
    0,                         /*tp_getattro*/
    0,                         /*tp_setattro*/
    0,                         /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,        /*tp_flags*/
    intcodec_doc,              /* tp_doc */
    0,		               /* tp_traverse */
    0,		               /* tp_clear */
    0,		               /* tp_richcompare */
    0,		               /* tp_weaklistoffset */
    0,		               /* tp_iter */
    0,		               /* tp_iternext */
    intcodec_methods,          /* tp_methods */
    codec_members,             /* tp_members */
    0,                         /* tp_getset */
    0,                         /* tp_base */
    0,                         /* tp_dict */
    0,                         /* tp_descr_get */
    0,                         /* tp_descr_set */
    0,                         /* tp_dictoffset */
    0,                         /* tp_init */
    0,                         /* tp_alloc */
    intcodec_new,              /* tp_new */
};


static char module_doc[] = 
"Reed-Solomon error correction library";

void
initreedsolomon()
{
    PyObject* m;

    if (PyType_Ready(&CodecType) < 0)
        return;
    if (PyType_Ready(&IntegerCodecType) < 0)
        return;

    m = Py_InitModule3("reedsolomon", module_methods, module_doc);

    Py_INCREF(&CodecType);
    Py_INCREF(&IntegerCodecType);
    if (PyModule_AddObject(m, "Codec",
                           (PyObject*) &CodecType) < 0)
        return;
    if (PyModule_AddObject(m, "IntegerCodec",
                           (PyObject*) &IntegerCodecType) < 0)
        return;
    UncorrectableError = PyErr_NewException("reedsolomon.UncorrectableError",
                                            NULL, NULL);
    if (!UncorrectableError)
        return;
    Py_INCREF(UncorrectableError);
    if (PyModule_AddObject(m, "UncorrectableError", UncorrectableError) < 0)
        return;
}
