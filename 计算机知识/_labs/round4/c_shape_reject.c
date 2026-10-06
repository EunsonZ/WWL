/* Expected diagnostic: incompatible pointer type, int (*)[3] is not int **. */
void needs_rows(int **p) {(void)p;}
int main(void){int matrix[2][3]={{0}};needs_rows(matrix);}
