rule Kali_Lab_Benign_Two_Markers {
    meta:
        description = "Benign synthetic teaching condition; NOT malware detection"
        fixture_version = "1.0"
    strings:
        $a = "KALI_LAB_MARKER_A" ascii
        $b = "KALI_LAB_MARKER_B" ascii
    condition:
        filesize < 4096 and all of them
}
