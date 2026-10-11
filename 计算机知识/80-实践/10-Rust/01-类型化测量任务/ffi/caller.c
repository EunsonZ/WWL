#include "wwl_measurement.h"
#include <assert.h>
#include <stdio.h>
_Static_assert(sizeof(WwlResult)==12,"result layout size");
_Static_assert(offsetof(WwlResult,position)==4,"position layout");
_Static_assert(offsetof(WwlResult,written)==8,"written layout");
int main(void) {
 uint16_t previous=0,input[]={2,4,6,8},output[]={99,99,99,99};
 WwlResult r=wwl_fir_process(&previous,input,2,output,2);
 assert(r.status==WWL_OK && r.written==2 && previous==4);
 r=wwl_fir_process(&previous,input+2,2,output+2,2);
 assert(r.status==WWL_OK && previous==8);
 uint16_t expected[]={2,6,10,14};
 for(size_t i=0;i<4;++i) assert(output[i]==expected[i]);
 uint16_t bad[]={2,4096},unchanged[]={99,99};
 r=wwl_fir_process(&previous,bad,2,unchanged,2);
 assert(r.status==WWL_INPUT_RANGE && r.position==2 && r.written==0);
 assert(previous==8 && unchanged[0]==99 && unchanged[1]==99);
 r=wwl_fir_process(&previous,NULL,0,NULL,0);assert(r.status==WWL_OK);
 r=wwl_fir_process(&previous,input,4,output,3);assert(r.status==WWL_OUTPUT_CAPACITY);
 r=wwl_fir_process(&previous,input,4,input,4);assert(r.status==WWL_OVERLAP);
 r=wwl_fir_process(NULL,input,4,output,4);assert(r.status==WWL_BAD_POINTER);
 r=wwl_fir_process(&previous,input,1025,output,4);assert(r.status==WWL_INPUT_LIMIT);
 previous=4096;r=wwl_fir_process(&previous,input,4,output,4);assert(r.status==WWL_STATE_RANGE && previous==4096);
 puts("C ABI: [2,4,6,8], twice-mV [2,6,10,14], persistent state, errors unchanged");
 return 0;
}
