# Source in a task subprocess only; does not modify global/system configuration.
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export ANDROID_SDK_ROOT=/private/tmp/wwl-next-175-env/sdk
export ANDROID_HOME=/private/tmp/wwl-next-175-env/sdk
export ANDROID_USER_HOME=/private/tmp/wwl-next-175-env/android-user
export ANDROID_AVD_HOME=/private/tmp/wwl-next-175-env/avd
export GRADLE_USER_HOME=/private/tmp/wwl-next-175-env/gradle-home
export PATH="$JAVA_HOME/bin:/private/tmp/wwl-next-175-env/gradle-8.9/bin:$ANDROID_SDK_ROOT/cmdline-tools/19.0/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH"
