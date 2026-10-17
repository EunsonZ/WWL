"""Apply one observational trace insertion to the pinned eSpeak NG 1.52.0 source.
Does not change synth arithmetic. The main lab verifies fixed-utterance PCM identity.
"""
from pathlib import Path
import argparse

INSERT=r'''
	/* WWL observational trace: fixed-point parameters and resulting harmonic table. */
	{
		static FILE *wwl_trace = NULL;
		static int wwl_checked = 0;
		static unsigned long wwl_index = 0;
		if (!wwl_checked) {
			const char *wwl_path = getenv("WWL_TTS_ACOUSTIC_TRACE");
			if (wwl_path && *wwl_path) {
				wwl_trace = fopen(wwl_path, "w");
				if (wwl_trace) {
					fprintf(wwl_trace, "dispatch,local_samplecount,control,pitch_hz,hmax");
					for (int j=0;j<6;j++) fprintf(wwl_trace, ",F%d_hz,L%d_hz,R%d_hz,height%d_raw",j,j,j,j);
					for (int j=1;j<=8;j++) fprintf(wwl_trace, ",harmonic%d_raw",j);
					fprintf(wwl_trace, "\n");
				}
			}
			wwl_checked=1;
		}
		if (wwl_trace) {
			fprintf(wwl_trace, "%lu,%d,%d,%.8f,%d",wwl_index++,samplecount,control,pitch/65536.0,hmax);
			for (int j=0;j<6;j++) fprintf(wwl_trace, ",%.8f,%.8f,%.8f,%d",peaks[j].freq/65536.0,peaks[j].left/65536.0,peaks[j].right/65536.0,peaks[j].height);
			for (int j=1;j<=8;j++) fprintf(wwl_trace, ",%d",j<=hmax?htab[j]:0);
			fprintf(wwl_trace,"\n");
			fflush(wwl_trace);
		}
	}
'''


def apply(path):
    text=path.read_text()
    if 'WWL observational trace' in text: return
    needle='\treturn hmax; // highest harmonic number'
    if text.count(needle)!=1:raise ValueError('pinned wavegen.c context must match exactly once')
    path.write_text(text.replace(needle,INSERT+'\n'+needle))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source_root',type=Path);a=p.parse_args();apply(a.source_root/'src/libespeak-ng/wavegen.c')
