#include <stddef.h>

void fill_rows(size_t rows, int a[][3]) {
    for (size_t i = 0; i < rows; ++i) {
        for (size_t j = 0; j < 3; ++j) {
            a[i][j] = 0;
        }
    }
}
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

bool dense_count(size_t rows, size_t cols, size_t *out) {
    if (out == NULL) return false;
    if (cols != 0 && rows > SIZE_MAX / cols) return false;
    *out = rows * cols;
    return true;
}
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <limits.h>

_Static_assert(CHAR_BIT == 8, "This protocol requires 8-bit bytes");

bool read_be32(const unsigned char *data, size_t size,
               size_t offset, uint32_t *out) {
    if (data == NULL || out == NULL) return false;
    if (offset > size || size - offset < 4) return false;
    uint32_t value = ((uint32_t)data[offset] << 24)
                   | ((uint32_t)data[offset + 1] << 16)
                   | ((uint32_t)data[offset + 2] << 8)
                   |  (uint32_t)data[offset + 3];
    *out = value;
    return true;
}
#include <assert.h>
#include <stdio.h>
int main(void) {
    int m[2][3]={{10,11,12},{20,21,22}};
    int (*row)[3]=m;
    assert(sizeof *row==3*sizeof(int));
    assert(row+1==&m[1]);
    assert((*(row+1))[2]==22);
    fill_rows(2,m);
    for(size_t i=0;i<2;++i) for(size_t j=0;j<3;++j) assert(m[i][j]==0);
    size_t count=99;
    assert(dense_count(2,3,&count)&&count==6);
    assert(dense_count(SIZE_MAX,0,&count)&&count==0);
    count=99;assert(!dense_count(SIZE_MAX,2,&count)&&count==99);
    assert(!dense_count(2,3,NULL));
    unsigned char data[]={0,1,2,3,4,255,254,253};
    uint32_t value=0;
    assert(read_be32(data,sizeof data,1,&value)&&value==UINT32_C(0x01020304));
    value=777;assert(!read_be32(data,sizeof data,SIZE_MAX,&value)&&value==777);
    assert(!read_be32(data,sizeof data,5,&value)&&value==777);
    assert(!read_be32(NULL,0,0,&value)&&value==777);
    assert(!read_be32(data,sizeof data,0,NULL));
    for(size_t offset=0;offset+4<=sizeof data;++offset){
        uint32_t expected=0;
        for(size_t i=0;i<4;++i) expected=expected*256u+data[offset+i];
        assert(read_be32(data,sizeof data,offset,&value)&&value==expected);
    }
    puts("C contract checks passed");
}
