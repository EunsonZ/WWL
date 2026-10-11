#include <wwl/measurement_abi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); ++failures; } } while (0)
int main(void) {
    int failures = 0;
    wwl_report_handle* h = NULL;
    wwl_report_settings_v1 s = {1000, 0, 1000, 2, 1, 3, {'a','b','i'}};
    wwl_report_layout_v1 layout;
    size_t required = 99;
    CHECK(wwl_report_get_layout_v1(1,sizeof layout,&layout)==WWL_OK);
    CHECK(layout.settings_size==sizeof s && layout.settings_alignment==_Alignof(wwl_report_settings_v1));
    CHECK(layout.gain_offset==offsetof(wwl_report_settings_v1,gain_uV_per_code));
    CHECK(layout.offset_offset==offsetof(wwl_report_settings_v1,offset_uV));
    CHECK(layout.interval_offset==offsetof(wwl_report_settings_v1,interval_ms));
    CHECK(layout.width_offset==offsetof(wwl_report_settings_v1,width));
    CHECK(layout.hop_offset==offsetof(wwl_report_settings_v1,hop));
    CHECK(layout.label_bytes_offset==offsetof(wwl_report_settings_v1,label_bytes));
    CHECK(layout.label_offset==offsetof(wwl_report_settings_v1,label));
    printf("C layout size=%zu align=%zu offsets=%u,%u,%u,%u,%u,%u,%u\n",sizeof s,
        (size_t)_Alignof(wwl_report_settings_v1),layout.gain_offset,layout.offset_offset,
        layout.interval_offset,layout.width_offset,layout.hop_offset,layout.label_bytes_offset,layout.label_offset);
    CHECK(wwl_report_create_v1(2,&h)==WWL_VERSION_MISMATCH && h==NULL);
    CHECK(wwl_report_create_v1(1,&h)==WWL_OK);
    if (!h) return 1;
    CHECK(wwl_report_copy_text_v1(h,NULL,0,&required)==WWL_NOT_READY && required==0);
    CHECK(wwl_report_replace_v1(h,2,0,NULL,NULL,0)==WWL_VERSION_MISMATCH);
    CHECK(wwl_report_replace_v1(h,1,0,NULL,NULL,0)==WWL_SIZE_MISMATCH);
    CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,"2 4 6 8",7)==WWL_OK);
    CHECK(wwl_report_copy_text_v1(h,NULL,0,&required)==WWL_BUFFER_TOO_SMALL);
    if (required==0) { wwl_report_destroy_v1(&h); return 1; }
    char* text = malloc(required+2);
    char* old = malloc(required);
    if (!text || !old) { free(text); free(old); wwl_report_destroy_v1(&h); return 1; }
    memset(text,'!',required+2);
    const size_t needed = required;
    CHECK(wwl_report_copy_text_v1(h,text+1,needed-1,&required)==WWL_BUFFER_TOO_SMALL);
    for (size_t i=0;i<needed+2;++i) CHECK(text[i]=='!');
    CHECK(wwl_report_copy_text_v1(h,text+1,needed,&required)==WWL_OK);
    CHECK(text[0]=='!' && text[needed+1]=='!' && text[needed]=='\0');
    memcpy(old,text+1,needed);
    CHECK(strstr(old,"count=4") && strstr(old,"windows=3"));
    CHECK(strstr(old,"first_ms=0 last_ms=1000 sum_mV=6 mean_mV=3 population_variance_mV2=1 rms_squared_mV2=10"));
    CHECK(strstr(old,"mean_mV=5") && strstr(old,"mean_mV=7"));
    CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,"2 bad 8",7)==WWL_INVALID_ARGUMENT);
    CHECK(wwl_report_copy_text_v1(h,text+1,needed,&required)==WWL_OK && !strcmp(old,text+1));
    CHECK(wwl_report_replace_v1(h,1,sizeof s,&s,NULL,0)==WWL_OK);
    CHECK(!strcmp(old,text+1)); /* Caller-owned output survived replacement. */
    CHECK(wwl_report_destroy_v1(&h)==WWL_OK && h==NULL);
    CHECK(!strcmp(old,text+1)); /* Caller-owned output also survived destruction. */
    CHECK(wwl_report_destroy_v1(&h)==WWL_OK); /* Null no-op, not a stale-handle test. */
    printf("%s",old);
    free(old); free(text);
    printf("installed C caller %s\n",failures ? "FAIL" : "PASS");
    return failures ? 1 : 0;
}
