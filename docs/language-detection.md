# A note on this scan

This note is what the play/002 search had to get right. The search runs on the Hebrew Psalter. The King James text is the control, not the corpus. A pattern is a citation only when a Hebrew verse shows it; otherwise it is a drop. This is not a manual for other languages.

The search runs on Hebrew. `test_kjv_string_alone_is_not_a_hit` gives `search()` the English sentence "Amen, and Amen" and the vendored King James Psalter. Both return no hits. A KJV string alone is not a hit.

A remembered pattern with no Hebrew verse is a drop. `test_remembered_pattern_with_no_hebrew_verse_is_a_drop` puts "Amen, and Amen" at King James 17:3 and "are ended" at 17:4. Hebrew psalm 17 has neither. The receipt drops both addresses and does not list them as hits.

The stored seam after 150 is a drop. `test_hypothesis_psalm_without_a_hebrew_formula_is_a_drop` reads Psalm 150 in the vendored Westminster Leningrad Codex. Its last two verses do not contain the Amen word, and they do not contain both כלו and תפלות. The remembered seam after 150 stays a drop. It is not promoted to a hit.

Substring is not a word. `test_hebrew_longer_word_containing_amen_letters_is_not_a_hit` uses אֲמָנוֹן. Its consonants contain אמן and then more letters, so it is not an Amen. A real Amen later in that psalm still is. `test_kjv_control_firmament_and_lamentation_are_not_amen` checks the English control: firmament, in Psalms 19 and 150, and lamentation are not Amen. The comma in "Amen, and Amen" does not stop the English word from counting, and it still does not make those lines hits.

Hebrew needs its own tokenizer. `test_hebrew_tokenizer_niqqud_cantillation_maqqef_and_leading_vav` strips vowel points and cantillation only to test the consonant skeleton. Maqqef and paseq stay punctuation, not extra words. A leading ו, as in וְאָמֵן, is still Amen. Any other extra consonant is not.

Pointing is reported, not interpreted. `test_hebrew_pointing_is_reported_not_interpreted` feeds אָ֘מֵ֥ן. The skeleton check drops the zarqa and the vowels so the consonants can be compared with אמן. The hit keeps that pointed token, zarqa and qamats included. The points are not assigned a meaning.

An English address is not forced onto the Hebrew verse. `test_english_control_address_is_dropped_when_the_hebrew_verse_differs` reads both vendored files. This run drops King James 41:13 and 89:52, and cites Hebrew 41:14 and 89:53. The scan does not rewrite one number onto the other. Where the numbers already agree, as at 72:19 and 106:48, the Hebrew line is the hit and the English line stays labeled control.

A blessing in the middle is not a seam. `test_hebrew_mid_psalm_blessing_is_not_a_seam` finds ברוך יהוה outside the last two verses of its psalm in the vendored Hebrew, including 28:6. Those lines are not hits. `test_blessing_alone_is_not_a_seam` checks a lone ברוך, a terminal ברוך יהוה with no Amen, and the English words "Blessed be the LORD". None of those is a seam.

One formula is not another. `test_hebrew_formulas_are_different_detectors` keeps three detectors apart: Amen plus and plus Amen, a single Amen, and a terminal verse that contains both whole words כלו and תפלות. The same two Hebrew words outside the last two verses are not that third detector.

The search key is the formula, not the stored list. `test_hebrew_synthetic_endings_off_the_five_book_list` is the proof. Its Hebrew endings are a double Amen at Psalms 3 and 8, not at 41, 72, 89, 106, or 150. The search reports 3 and 8. The stored list is applied only afterward, as drops for psalms with no Hebrew citation. It is not a seed.

Not scanned is not the same as absent. `test_hebrew_not_scanned_is_not_reported_as_absent` reads the search item. Acrostics, qere/ketiv, cantillation-as-seam, and manuscript layout (blank lines between books) are listed as not scanned. This run has no detector for them, so it does not report a miss. A missing detector cannot be reported as a miss.

Which text was opened is part of the claim. `test_search_opens_wlc_text_and_not_morphology` checks the vendored file: public-domain Westminster Leningrad Codex text from eBible hboWLC and the Groves Center, with no Strong numbers and no morphology fields. The search item says morphology, BHS, and BHQ were not opened. The King James text is labeled control. `test_receipt_does_not_claim_the_setup` checks that the page does not say the search found a setup.

A hit has to point at a Hebrew verse. `test_every_hit_points_at_a_vendored_hebrew_verse` checks each hit's pointed words against that verse in the vendored Hebrew, and it fails a hit that has no verse.
