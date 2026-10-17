from pathlib import Path
import subprocess,os,shutil,json,hashlib
r=Path(__file__).resolve().parent;s=r/'resource-final-source';out=r/'resource-final-apks';env=os.environ.copy();env.update({'JAVA_HOME':'/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home','ANDROID_SDK_ROOT':'/private/tmp/wwl-next-175-env/sdk','ANDROID_HOME':'/private/tmp/wwl-next-175-env/sdk','ANDROID_USER_HOME':'/private/tmp/wwl-next-175-env/android-user','GRADLE_USER_HOME':'/private/tmp/wwl-next-175-env/gradle-home','JAVA_TOOL_OPTIONS':'-Duser.home=/private/tmp/wwl-next-175-env/java-user -XX:ActiveProcessorCount=1'})
gradle='/private/tmp/wwl-next-175-env/gradle-8.9/bin/gradle';records=[]
for name,version,fail,kind in [('bad-v2-db2',2,'true','Debug'),('good-v2-db2',2,'false','Debug'),('v3-release-unsigned',3,'false','Release')]:
 cmd=[gradle,'--no-daemon','--max-workers=1','-p',str(s),':networkApp:assembleR'+kind,'-PcourseVersion='+str(version),'-PcourseDbVersion=2','-PfailMigration='+fail]
 with (r/('final-'+name+'-build.log')).open('w') as f:subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 src=s/'networkApp/build/outputs/apk/r'/kind.lower()/('networkApp-r-debug.apk' if kind=='Debug' else 'networkApp-r-release-unsigned.apk');dst=out/(name+'.apk');shutil.copy2(src,dst);records.append({'argv':cmd,'output':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()});(out/'build-commands.json').write_text(json.dumps(records,indent=2));print(name,'built',flush=True)
