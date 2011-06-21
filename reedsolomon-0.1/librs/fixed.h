/* Configure the RS codec with fixed parameters for CCSDS standard
 * (255,223) code over GF(256). Note: the conventional basis is still
 * used; the dual-basis mappings are performed in [en|de]code_rs_ccsds.c
 *
 * Copyright 2002 Phil Karn, KA9Q
 * May be used under the terms of the GNU General Public License (GPL)
 */
#define DTYPE unsigned char

static inline int mod255(int x){
  while (x >= 255) {
    x -= 255;
    x = (x >> 8) + (x & 255);
  }
  return x;
}
#define MODNN(x) mod255(x)

extern DTYPE CCSDS_alpha_to[];
extern DTYPE CCSDS_index_of[];
extern DTYPE CCSDS_poly[];

#define MM 8
#define NN 255
#define ALPHA_TO CCSDS_alpha_to
#define INDEX_OF CCSDS_index_of
#define GENPOLY CCSDS_poly
#define NROOTS 32
#define FCR 112
#define PRIM 11
#define IPRIM 116
#define PAD pad
#define A0 ((DTYPE)(NN))

#define ENCODE_RS encode_rs_8
#define DECODE_RS decode_rs_8

void ENCODE_RS(DTYPE *data,DTYPE *parity,int pad);
int DECODE_RS(DTYPE *data, int *eras_pos, int no_eras,int pad);
