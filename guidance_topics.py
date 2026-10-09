"""The "Ask the Quran" library: common life situations, each with ayat, sahih hadith and short guidance.
Edit here, then run  python build_guidance.py  which checks every reference against the Quran data and
the hadith collections and writes guidance.json (what the website reads).

ayat:   "surah:ayah" or "surah:first-last"
hadith: (collection, hadith number in the fawazahmed0 hadith-api edition); only Sahih al-Bukhari and
        Sahih Muslim are used, so every hadith shown is sahih.
words:  what people may type (English, Roman Urdu, Urdu); matched loosely."""

TOPICS = [
    dict(id="anxiety", en="Anxiety and worry", ur="پریشانی اور فکر",
         words="anxiety anxious worry worried stress stressed tension nervous overthinking panic restless fear future "
               "pareshan pareshani fikar tension ghabrahat dar bechaini پریشان پریشانی فکر گھبراہٹ بے چینی ڈر",
         ayat=["13:28", "2:286", "94:5-6"], hadith=[("bukhari", 6369), ("muslim", 7500)],
         guide_en="Worry is part of being human. The Quran teaches that hearts find rest in remembering Allah, that no "
                  "soul is burdened beyond what it can bear, and that ease comes with hardship. Do what is in your hands, "
                  "then leave the outcome to Allah. The Prophet ﷺ himself asked Allah for refuge from worry and grief, so "
                  "make that dua part of your day.",
         guide_ur="پریشانی انسان کی فطرت کا حصہ ہے۔ قرآن بتاتا ہے کہ دل اللہ کے ذکر سے سکون پاتے ہیں، کسی جان پر طاقت سے زیادہ "
                  "بوجھ نہیں ڈالا جاتا، اور مشکل کے ساتھ آسانی ہے۔ جو آپ کے بس میں ہے وہ کریں اور نتیجہ اللہ پر چھوڑ دیں۔"),
    dict(id="sadness", en="Sadness and low mood", ur="غم اور اداسی",
         words="sad sadness depressed depression unhappy down low cry crying broken heartbroken hopeless empty "
               "udaas udasi gham dukh rona dil toot مایوس اداس اداسی غم دکھ رونا",
         ayat=["12:86", "94:5-6", "93:3-5"], hadith=[("bukhari", 5641), ("muslim", 7500)],
         guide_en="Sadness is not a sign of weak faith. Prophet Yaqub said he complains of his grief only to Allah, and "
                  "Allah reassured the Prophet ﷺ that He had not abandoned him. Every pain a believer feels is not wasted. "
                  "Talk to Allah, talk to someone you trust, and if sadness stays for weeks, please also see a doctor or "
                  "counsellor: that is part of looking after the trust of your body and mind.",
         guide_ur="اداسی کمزور ایمان کی علامت نہیں۔ حضرت یعقوبؑ نے اپنا غم صرف اللہ سے کہا۔ مومن کا کوئی دکھ ضائع نہیں جاتا۔ "
                  "اللہ سے بات کریں، کسی بھروسے والے سے بات کریں، اور اگر اداسی ہفتوں رہے تو ڈاکٹر سے بھی ضرور ملیں۔"),
    dict(id="anger", en="Anger", ur="غصہ",
         words="anger angry rage temper mad furious shout shouting fight frustrated irritated "
               "gussa ghussa naraz jhagra chillana غصہ ناراض جھگڑا",
         ayat=["3:133-134", "42:37"], hadith=[("bukhari", 6114), ("bukhari", 6116)],
         guide_en="Real strength is controlling yourself when angry. Allah praises those who swallow their anger and "
                  "forgive people. When anger rises, stay silent, change your position, make wudu, and seek refuge in "
                  "Allah from Shaytan. Decide nothing until you are calm.",
         guide_ur="اصل طاقت غصے کے وقت خود پر قابو رکھنا ہے۔ اللہ غصہ پی جانے اور معاف کرنے والوں کو پسند کرتا ہے۔ غصہ آئے تو "
                  "خاموش ہو جائیں، جگہ بدلیں، وضو کریں اور اعوذ باللہ پڑھیں۔ پرسکون ہونے تک کوئی فیصلہ نہ کریں۔"),
    dict(id="patience", en="Patience in hard times", ur="مشکل وقت میں صبر",
         words="patience patient hardship difficult difficulty struggle trial test problems tough suffering calamity "
               "sabr mushkil musibat azmaish takleef صبر مشکل مصیبت آزمائش تکلیف",
         ayat=["2:153", "2:155-157", "39:10"], hadith=[("muslim", 7500), ("bukhari", 1469)],
         guide_en="Trials are part of every life, and Allah is with those who are patient. Patience is not giving up: it "
                  "is staying steady, praying, and keeping going while trusting Allah. The Prophet ﷺ said whoever tries to "
                  "be patient, Allah makes him patient.",
         guide_ur="آزمائش ہر زندگی کا حصہ ہے اور اللہ صبر کرنے والوں کے ساتھ ہے۔ صبر ہار ماننا نہیں بلکہ ثابت قدم رہنا، نماز "
                  "پڑھنا اور اللہ پر بھروسے کے ساتھ آگے بڑھنا ہے۔"),
    dict(id="illness", en="Illness", ur="بیماری",
         words="ill illness sick sickness disease pain hospital cancer health treatment surgery "
               "bimar bimari marz dard hospital ilaj بیمار بیماری مرض درد علاج",
         ayat=["26:80", "17:82", "2:286"], hadith=[("bukhari", 5678), ("bukhari", 5641)],
         guide_en="Allah is the One who cures, and He has sent a cure for every disease, so seeking treatment is part "
                  "of trusting Him, not against it. Pain and illness wipe away sins for the believer. Take your "
                  "medicine, make dua, and let the people around you help you.",
         guide_ur="شفا دینے والا اللہ ہے، اور اس نے ہر بیماری کی دوا اتاری ہے، اس لیے علاج کروانا توکل کا حصہ ہے۔ بیماری "
                  "مومن کے گناہ مٹاتی ہے۔ دوا لیں، دعا کریں اور اپنوں کی مدد قبول کریں۔"),
    dict(id="grief", en="Death of a loved one", ur="کسی پیارے کی وفات",
         words="death died dead passed away loss lost funeral grief grieving mourning mother father died "
               "maut wafat inteqal faut janaza wafaat موت وفات انتقال جنازہ",
         ayat=["2:155-157", "3:185", "29:57"], hadith=[("muslim", 2126), ("bukhari", 1283)],
         guide_en="Grief is love that has nowhere to go, and tears are not wrong: the Prophet ﷺ wept too. Every soul "
                  "returns to Allah. Say inna lillahi wa inna ilayhi raji'un, make dua for the one you lost, give "
                  "charity on their behalf, and be gentle with yourself while you heal.",
         guide_ur="آنسو بہانا غلط نہیں، نبی ﷺ بھی روئے۔ ہر جان اللہ کی طرف لوٹتی ہے۔ انا للہ وانا الیہ راجعون پڑھیں، مرحوم "
                  "کے لیے دعا اور صدقہ کریں، اور خود پر نرمی رکھیں۔"),
    dict(id="parents", en="Parents", ur="والدین",
         words="parents mother father mom mum dad mummy papa ammi abbu abba maa baap walidain "
               "والدین ماں باپ امی ابو",
         ayat=["17:23-24", "31:14", "46:15"], hadith=[("bukhari", 5971), ("bukhari", 527)],
         guide_en="After worshipping Allah, the Quran puts kindness to parents first. Speak to them gently, never with "
                  "even a word of annoyance, and pray for them. Even when you disagree, stay respectful: serving them is "
                  "one of the deeds most loved by Allah.",
         guide_ur="اللہ کی عبادت کے بعد قرآن والدین سے حسن سلوک کو رکھتا ہے۔ ان سے نرمی سے بات کریں، اف تک نہ کہیں اور ان کے "
                  "لیے دعا کریں۔ اختلاف ہو تب بھی ادب نہ چھوڑیں۔"),
    dict(id="marriage", en="Marriage and spouse", ur="شادی اور میاں بیوی",
         words="marriage married husband wife spouse rishta nikah shadi divorce talaq relationship partner "
               "shohar biwi miyan شادی نکاح شوہر بیوی طلاق رشتہ",
         ayat=["30:21", "4:19"], hadith=[("muslim", 3648)],
         guide_en="Allah made spouses a source of peace, with love and mercy between them, and asks husbands to live "
                  "with their wives in kindness. No spouse is perfect; the Prophet ﷺ taught that if you "
                  "dislike one quality, you will be pleased with another. Speak kindly and solve problems together.",
         guide_ur="اللہ نے میاں بیوی کو ایک دوسرے کے لیے سکون بنایا اور ان کے درمیان محبت اور رحمت رکھی۔ کوئی بھی کامل نہیں، "
                  "ایک بات ناپسند ہو تو دوسری اچھی لگے گی۔ نرمی سے بات کریں اور مل کر مسائل حل کریں۔"),
    dict(id="children", en="Children", ur="اولاد",
         words="children child kids son daughter baby raising parenting no children infertility "
               "bacche bachay beta beti aulad اولاد بچے بیٹا بیٹی",
         ayat=["25:74", "18:46", "8:28"], hadith=[("bukhari", 5997), ("muslim", 4223)],
         guide_en="Children are a blessing and a trust. Show them mercy and affection: the Prophet ﷺ kissed his "
                  "grandchildren and said whoever does not show mercy is not shown mercy. A righteous child is a reward "
                  "that continues after you die. Ask Allah to make your family a comfort to your eyes.",
         guide_ur="اولاد نعمت بھی ہے اور امانت بھی۔ ان سے محبت اور شفقت کریں۔ نیک اولاد مرنے کے بعد بھی اجر کا ذریعہ ہے۔"),
    dict(id="rizq", en="Money, job and provision", ur="رزق، روزگار اور پیسہ",
         words="money job work business salary unemployed debt loan poor poverty rich income rent bills "
               "rizq rozi naukri paisa karz qarz garibi kaam kaarobar رزق روزی نوکری پیسہ قرض غربت کام",
         ayat=["65:3", "11:6", "71:10-12"], hadith=[("bukhari", 6446), ("bukhari", 2072), ("bukhari", 6369)],
         guide_en="Your provision is written by Allah, and whoever is mindful of Him, He provides from where they do not "
                  "expect. Work honestly: the best food is what you earn with your own hands. Seek forgiveness often, "
                  "avoid unnecessary debt, and remember that real richness is contentment of the heart.",
         guide_ur="رزق اللہ نے لکھ دیا ہے، اور جو اللہ سے ڈرتا ہے اسے وہاں سے دیتا ہے جہاں سے گمان بھی نہ ہو۔ حلال محنت کریں، "
                  "استغفار کثرت سے کریں، اور یاد رکھیں کہ اصل امیری دل کا غنا ہے۔"),
    dict(id="study", en="Exams, studies and knowledge", ur="امتحان اور تعلیم",
         words="exam exams test study studies school college university result marks fail failed knowledge learn "
               "imtihan imtehan parhai padhai result fail ilm امتحان پڑھائی تعلیم علم نتیجہ",
         ayat=["20:114", "58:11", "94:5-6"], hadith=[("muslim", 6853), ("bukhari", 71)],
         guide_en="Seeking knowledge is worship, and the path of learning is a path to Paradise. Prepare well, then trust "
                  "Allah with the result. Say: my Lord, increase me in knowledge. A bad result is not the end of your "
                  "story; with hardship comes ease.",
         guide_ur="علم حاصل کرنا عبادت ہے اور علم کا راستہ جنت کا راستہ ہے۔ اچھی تیاری کریں اور نتیجہ اللہ پر چھوڑیں۔ رب زدنی علما "
                  "پڑھتے رہیں۔"),
    dict(id="sin", en="Guilt and repentance", ur="گناہ اور توبہ",
         words="sin sins sinned guilt guilty repent repentance shame regret haram mistake mistakes bad deeds "
               "gunah tauba toba maafi sharminda گناہ توبہ معافی شرمندہ",
         ayat=["39:53", "4:110", "25:70"], hadith=[("bukhari", 6307), ("muslim", 6965)],
         guide_en="Never despair of Allah's mercy: He forgives all sins for those who return to Him. The Prophet ﷺ sought "
                  "forgiveness more than seventy times a day. Stop the sin, regret it, sincerely intend not to return, and "
                  "repair any harm to people. Allah can even turn bad deeds into good ones.",
         guide_ur="اللہ کی رحمت سے کبھی مایوس نہ ہوں، وہ توبہ کرنے والوں کے سب گناہ معاف کرتا ہے۔ گناہ چھوڑیں، ندامت کریں، "
                  "دوبارہ نہ کرنے کا ارادہ کریں اور اگر کسی کا حق ہے تو ادا کریں۔"),
    dict(id="forgive", en="Forgiving someone who hurt you", ur="کسی کو معاف کرنا",
         words="forgive forgiving forgiveness pardon hurt betrayed revenge grudge wronged someone hurt me "
               "maaf muaf badla dhoka dil dukhaya معاف بدلہ دھوکہ",
         ayat=["24:22", "42:40", "7:199"], hadith=[("muslim", 6592)],
         guide_en="Forgiving is not saying what happened was fine; it is freeing your heart. Allah asks: do you not love "
                  "that Allah should forgive you? Whoever pardons, Allah raises their honour. You may still protect "
                  "yourself and set boundaries while you forgive.",
         guide_ur="معاف کرنا ظلم کو درست کہنا نہیں بلکہ اپنے دل کو آزاد کرنا ہے۔ کیا آپ نہیں چاہتے کہ اللہ آپ کو معاف کرے؟ معاف "
                  "کرنے والے کی عزت اللہ بڑھاتا ہے۔"),
    dict(id="lonely", en="Loneliness", ur="تنہائی",
         words="lonely loneliness alone no friends nobody isolated left alone "
               "akela akelapan tanhai koi nahi تنہا تنہائی اکیلا",
         ayat=["2:186", "50:16", "57:4"], hadith=[("bukhari", 7405)],
         guide_en="You are never truly alone: Allah is near and answers the one who calls Him, closer than your jugular "
                  "vein. Allah says He is as His servant thinks of Him and is with him when he remembers Him. Reach out to "
                  "the masjid, family or a good friend too.",
         guide_ur="آپ کبھی اکیلے نہیں، اللہ قریب ہے اور پکارنے والے کی سنتا ہے۔ اللہ کو یاد کریں، اور مسجد، خاندان یا اچھے دوستوں "
                  "سے بھی رابطہ رکھیں۔"),
    dict(id="gratitude", en="Gratitude and contentment", ur="شکر اور قناعت",
         words="gratitude grateful thankful ungrateful compare comparison jealous of others never enough contentment "
               "shukar shukr qanaat شکر قناعت",
         ayat=["14:7", "2:152", "31:12"], hadith=[("muslim", 7430), ("muslim", 7500)],
         guide_en="If you are grateful, Allah will give you more. Look at those who have less than you, not more, so you "
                  "do not belittle Allah's blessings on you. Count three blessings every day and thank Allah for them.",
         guide_ur="شکر کرو گے تو اللہ اور دے گا۔ اپنے سے کم والوں کو دیکھیں، زیادہ والوں کو نہیں، تاکہ اللہ کی نعمتوں کی ناقدری "
                  "نہ ہو۔"),
    dict(id="envy", en="Jealousy and envy", ur="حسد",
         words="jealous jealousy envy envious hasad compare others success "
               "hasad jalan حسد جلن",
         ayat=["4:32", "113:1-5"], hadith=[("bukhari", 13), ("bukhari", 73)],
         guide_en="Do not wish for what Allah has given others; ask Allah from His bounty instead. Faith is complete when "
                  "you love for your brother what you love for yourself. When you feel envy, make dua for that person's "
                  "blessing to increase.",
         guide_ur="دوسروں کی نعمت کی تمنا نہ کریں بلکہ اللہ سے اس کا فضل مانگیں۔ ایمان یہ ہے کہ اپنے بھائی کے لیے وہی پسند کریں "
                  "جو اپنے لیے پسند کرتے ہیں۔"),
    dict(id="honesty", en="Honesty and lying", ur="سچائی اور جھوٹ",
         words="lie lied lies lying liar honest honesty truth truthful cheat cheated cheating trust "
               "jhoot jhooth sach sachai جھوٹ سچ سچائی",
         ayat=["9:119", "33:70-71"], hadith=[("bukhari", 6094), ("bukhari", 33)],
         guide_en="Truthfulness leads to goodness and goodness leads to Paradise. Speak the truth even when it is hard, "
                  "and Allah will set your deeds right. Lying, breaking promises and betraying trust are signs of "
                  "hypocrisy, so guard against them.",
         guide_ur="سچ نیکی کی طرف اور نیکی جنت کی طرف لے جاتی ہے۔ مشکل ہو تب بھی سچ بولیں۔ جھوٹ، وعدہ خلافی اور خیانت منافق کی "
                  "نشانیاں ہیں۔"),
    dict(id="future", en="Career, decisions and the future", ur="مستقبل اور فیصلے",
         words="future career decision decide choice confused what to do plan success fail failure goal dream "
               "mustaqbil faisla career kamyabi naakami مستقبل فیصلہ کامیابی ناکامی",
         ayat=["65:3", "3:159", "94:5-6"], hadith=[("muslim", 6774)],
         guide_en="Plan, consult people you trust, pray istikhara, then decide and rely on Allah: He is enough for "
                  "whoever relies on Him. The Prophet ﷺ said: strive for what benefits you, seek Allah's help, and do not "
                  "give up; and if something happens, do not say 'if only', but 'Allah decreed it'.",
         guide_ur="منصوبہ بنائیں، مشورہ کریں، استخارہ کریں، پھر فیصلہ کر کے اللہ پر بھروسہ کریں، جو اللہ پر بھروسہ کرے اللہ اس کے لیے کافی ہے۔"),
    dict(id="prayer", en="Struggling with prayer", ur="نماز میں سستی",
         words="prayer pray salah salat namaz namaaz lazy miss prayers fajr motivation iman low faith weak "
               "namaz susti iman kamzor نماز سستی ایمان",
         ayat=["2:45", "29:45", "20:14"], hadith=[("bukhari", 528), ("bukhari", 527)],
         guide_en="Prayer is a help, not a burden: seek help through patience and prayer. Five daily prayers wash sins "
                  "away like bathing five times a day. Start small: pray the next prayer on time, then the next. Allah "
                  "loves deeds done consistently, even if small.",
         guide_ur="نماز مدد ہے، بوجھ نہیں۔ پانچ نمازیں گناہوں کو ایسے دھوتی ہیں جیسے دن میں پانچ بار نہانا۔ اگلی نماز وقت پر "
                  "پڑھنے سے شروع کریں۔"),
    dict(id="friends", en="Friends and company", ur="دوستی اور صحبت",
         words="friend friends friendship company bad friends peer pressure toxic people "
               "dost dosti sohbat دوست دوستی صحبت",
         ayat=["25:27-29", "43:67", "18:28"], hadith=[("bukhari", 2101)],
         guide_en="You become like those you sit with. A good friend is like a perfume seller: you benefit even by being "
                  "near them. Choose friends who remind you of Allah, and gently distance yourself from those who pull "
                  "you towards harm.",
         guide_ur="انسان اپنے دوستوں جیسا بن جاتا ہے۔ اچھا دوست عطر بیچنے والے کی طرح ہے۔ ایسے دوست چنیں جو اللہ کی یاد دلائیں۔"),
    dict(id="pride", en="Arrogance and ego", ur="تکبر",
         words="arrogance arrogant pride proud ego show off showing off "
               "takabbur ghamand ghuroor تکبر غرور گھمنڈ",
         ayat=["31:18-19", "17:37"], hadith=[("muslim", 265)],
         guide_en="Allah does not love the arrogant. Even an atom's weight of pride is dangerous. Remember that every "
                  "blessing you have is from Allah, walk humbly, and treat people with respect whatever their status.",
         guide_ur="اللہ تکبر کرنے والوں کو پسند نہیں کرتا، ذرہ بھر تکبر بھی خطرناک ہے۔ ہر نعمت اللہ کی ہے، عاجزی اختیار کریں۔"),
    dict(id="backbiting", en="Backbiting and gossip", ur="غیبت",
         words="backbiting gossip talk behind back rumours slander bad mouth "
               "gheebat ghibat chugli غیبت چغلی",
         ayat=["49:12", "49:11"], hadith=[("muslim", 6593), ("bukhari", 6018)],
         guide_en="Backbiting is mentioning about your brother what he would dislike, even if it is true. The Quran "
                  "compares it to eating a dead brother's flesh. Speak good or stay silent, and if you have backbitten, "
                  "repent and speak well of that person.",
         guide_ur="غیبت یہ ہے کہ بھائی کے بارے میں ایسی بات کہی جائے جو اسے ناپسند ہو، چاہے سچ ہو۔ اچھی بات کہیں یا خاموش رہیں۔"),
    dict(id="neighbours", en="Neighbours and kindness to others", ur="پڑوسی اور حسن سلوک",
         words="neighbour neighbor neighbours kindness helping others community "
               "padosi hamsaya پڑوسی ہمسایہ",
         ayat=["4:36"], hadith=[("bukhari", 6014), ("bukhari", 6018)],
         guide_en="Jibril kept advising the Prophet ﷺ about neighbours until he thought they would inherit. Be kind to "
                  "neighbours, relatives, the poor and travellers, and never harm the people around you.",
         guide_ur="جبرائیلؑ پڑوسی کے بارے میں اتنی تاکید کرتے رہے کہ نبی ﷺ کو گمان ہوا کہ اسے وارث بنا دیا جائے گا۔ پڑوسیوں کو "
                  "تکلیف نہ دیں۔"),
    dict(id="oppression", en="When someone wrongs you", ur="جب کوئی ظلم کرے",
         words="injustice unfair oppression oppressed wronged bullied bully harassed abuse cheated "
               "zulm na insafi zalim ظلم ناانصافی ظالم",
         ayat=["14:42", "42:40-43"], hadith=[("bukhari", 2448)],
         guide_en="Allah is not unaware of what the wrongdoers do. There is no barrier between the prayer of the "
                  "oppressed and Allah. Seek justice through the right channels, protect yourself, and leave the rest "
                  "to Allah. If you are in danger, contact someone you trust or the police.",
         guide_ur="اللہ ظالموں کے کاموں سے غافل نہیں۔ مظلوم کی دعا اور اللہ کے درمیان کوئی پردہ نہیں۔ جائز طریقے سے انصاف مانگیں "
                  "اور خطرہ ہو تو مدد حاصل کریں۔"),
    dict(id="hope", en="Hope and Allah's mercy", ur="امید اور اللہ کی رحمت",
         words="hope hopeless despair give up giving up no way out mercy "
               "umeed na umeed mayoos rehmat امید ناامید مایوس رحمت",
         ayat=["12:87", "39:53", "94:5-6"], hadith=[("bukhari", 6000)],
         guide_en="Do not despair of Allah's mercy; only those without faith despair. Allah divided mercy into a hundred "
                  "parts and sent down only one to this world, from which all creatures show kindness. Hardship never "
                  "comes without ease alongside it.",
         guide_ur="اللہ کی رحمت سے مایوس نہ ہوں۔ اللہ نے رحمت کے سو حصے کیے اور دنیا میں صرف ایک اتارا۔ مشکل کے ساتھ آسانی ضرور ہے۔"),
    dict(id="dunya", en="Death, the afterlife and this world", ur="دنیا اور آخرت",
         words="death afterlife akhirah hereafter dunya world worldly materialism meaning of life purpose "
               "akhirat dunya maqsad زندگی کا مقصد آخرت دنیا",
         ayat=["3:185", "29:64", "51:56"], hadith=[("bukhari", 6416)],
         guide_en="This life is short and the home of the Hereafter is the true life. We were created to worship Allah. "
                  "Live in this world like a stranger or a traveller: enjoy what is good, but keep your heart on the "
                  "destination.",
         guide_ur="یہ زندگی مختصر ہے اور آخرت ہی اصل زندگی ہے۔ دنیا میں اجنبی یا مسافر کی طرح رہیں۔"),
    dict(id="desire", en="Temptation and desires", ur="خواہشات اور فتنے",
         words="temptation desire lust addiction porn haram relationship zina control myself "
               "nafs khwahish fitna شہوت نفس خواہش فتنہ",
         ayat=["79:40-41", "12:53", "24:30-31"], hadith=[("bukhari", 6474), ("bukhari", 5066)],
         guide_en="Whoever restrains the soul from its desires, Paradise is their home. Lower your gaze, avoid what "
                  "leads you to sin, and keep busy with good. The Prophet ﷺ advised young people to marry if they can, "
                  "and to fast if they cannot. Every time you resist, you grow stronger.",
         guide_ur="جو نفس کو خواہشات سے روکے، جنت اس کا ٹھکانا ہے۔ نظریں نیچی رکھیں، گناہ کے راستوں سے بچیں، اور نکاح نہ کر سکیں "
                  "تو روزہ رکھیں۔"),
    dict(id="charity", en="Charity and greed", ur="صدقہ اور بخل",
         words="charity sadaqa sadaqah zakat give donate greedy stingy miser "
               "sadqa sadaqa zakat kanjoos bukhl صدقہ زکوٰۃ کنجوس بخل",
         ayat=["2:261", "3:92"], hadith=[("bukhari", 1410), ("muslim", 6592)],
         guide_en="Spending in Allah's path is like a seed that grows seven hundredfold, and charity never decreases "
                  "wealth. Even a single date given from honest earnings is accepted and grown by Allah. Give regularly, "
                  "even if small.",
         guide_ur="اللہ کی راہ میں خرچ ایک دانے کی طرح ہے جو سات سو گنا بڑھتا ہے، اور صدقہ مال کم نہیں کرتا۔ تھوڑا ہی سہی، باقاعدگی "
                  "سے دیں۔"),
    dict(id="time", en="Wasting time and laziness", ur="وقت کا ضیاع اور سستی",
         words="time waste wasting lazy laziness procrastination scrolling social media productive "
               "waqt sust susti waqt barbad وقت سستی کاہلی",
         ayat=["103:1-3"], hadith=[("bukhari", 6412), ("bukhari", 6369)],
         guide_en="By time, humanity is in loss, except those who believe, do good, and encourage truth and patience. "
                  "Health and free time are two blessings many people lose. Plan your day, put your phone away during "
                  "prayer and study, and ask Allah for refuge from laziness.",
         guide_ur="زمانے کی قسم، انسان خسارے میں ہے سوائے ایمان اور نیک عمل والوں کے۔ صحت اور فارغ وقت دو نعمتیں ہیں جن میں لوگ "
                  "نقصان اٹھاتے ہیں۔"),
    dict(id="character", en="Good character and manners", ur="اچھے اخلاق",
         words="character manners behaviour behavior good person akhlaq rude harsh "
               "akhlaq tameez بداخلاقی اخلاق تمیز",
         ayat=["68:4", "33:21", "17:53"], hadith=[("bukhari", 6029), ("bukhari", 6125)],
         guide_en="The Prophet ﷺ was of great character, and the best of us are those with the best manners. Make "
                  "things easy for people, speak the best words, and treat others as you would like to be treated.",
         guide_ur="نبی ﷺ عظیم اخلاق والے تھے، اور تم میں بہترین وہ ہے جس کے اخلاق بہترین ہوں۔ لوگوں کے لیے آسانی پیدا کریں۔"),
    dict(id="family", en="Family conflict and ties of kinship", ur="رشتے داری اور خاندانی جھگڑے",
         words="family relatives fight brother sister cousin in laws cut off relations kinship "
               "rishtedar bhai behan khandan saas sasural قطع رحمی رشتہ دار بھائی بہن خاندان",
         ayat=["47:22-23", "4:1", "13:21"], hadith=[("bukhari", 5986), ("bukhari", 5991)],
         guide_en="Keeping family ties brings blessing in your life and provision. The one who truly keeps ties is the "
                  "one who reaches out even when others cut them off. Make the first call, forgive, and keep it simple.",
         guide_ur="صلہ رحمی سے عمر اور رزق میں برکت ہوتی ہے۔ اصل صلہ رحمی یہ ہے کہ کوئی تعلق توڑے تو بھی آپ جوڑیں۔"),
    dict(id="intention", en="Sincerity and intention", ur="نیت اور اخلاص",
         words="intention niyyah sincerity sincere showing off riya people pleasing "
               "niyat ikhlas dikhawa نیت اخلاص دکھاوا",
         ayat=["98:5", "6:162"], hadith=[("bukhari", 1)],
         guide_en="Actions are judged by intentions. Do good for Allah, not to impress people, and even ordinary "
                  "things like work, study and caring for family become worship when your intention is right.",
         guide_ur="اعمال کا دارومدار نیتوں پر ہے۔ ہر کام اللہ کے لیے کریں، دکھاوے کے لیے نہیں۔"),
    dict(id="qiyamah", en="The end of the world and the Day of Judgement", ur="قیامت اور دنیا کا خاتمہ",
         words="qiyamah qiyamat qayamat kayamat end of the world doomsday judgement day last day hour signs "
               "duniya dunya khatam akhri zamana قیامت دنیا ختم آخری زمانہ",
         ayat=["7:187", "33:63", "31:34"], hadith=[("bukhari", 3688), ("bukhari", 4936)],
         guide_en="Only Allah knows when the Hour will come; even the Prophet ﷺ was told to say its knowledge is with "
                  "his Lord. He also said his coming and the Hour are close, like two fingers side by side. When a man "
                  "asked him when it would be, he answered: what have you prepared for it? So the better question is "
                  "how to be ready: pray, do good, and love Allah and His Messenger.",
         guide_ur="قیامت کب آئے گی، یہ صرف اللہ جانتا ہے۔ نبی ﷺ نے فرمایا کہ میں اور قیامت ان دو انگلیوں کی طرح قریب ہیں۔ "
                  "ایک شخص نے پوچھا قیامت کب ہے تو آپ ﷺ نے فرمایا: تم نے اس کے لیے کیا تیاری کی ہے؟ اصل سوال تیاری کا ہے۔"),
    dict(id="dua", en="When your dua seems unanswered", ur="جب دعا قبول ہوتی نظر نہ آئے",
         words="dua duaa prayer answered unanswered accepted not accepted allah not listening allah not hearing "
               "qabool qubool sunta sunna دعا قبول سنتا",
         ayat=["2:186", "40:60", "27:62"], hadith=[("muslim", 6934)],
         guide_en="Allah is near and answers the one who calls on Him. The Prophet ﷺ said your dua is answered as long "
                  "as you do not grow impatient and say 'I prayed but was not answered'. An answer may come as what you "
                  "asked, as harm turned away, or as reward saved for you. Keep asking, with patience and trust.",
         guide_ur="اللہ قریب ہے اور پکارنے والے کی دعا سنتا ہے۔ نبی ﷺ نے فرمایا دعا قبول ہوتی ہے جب تک بندہ جلدی نہ کرے اور یہ "
                  "نہ کہے کہ میں نے دعا کی مگر قبول نہ ہوئی۔ صبر اور یقین سے مانگتے رہیں۔"),
    dict(id="crisis", en="Feeling like giving up on life", ur="زندگی سے مایوسی",
         words="suicide suicidal kill myself end my life want to die self harm hurt myself no reason to live "
               "khudkushi mar jana marna chahta zindagi khatam خودکشی مرنا چاہتا زندگی ختم",
         ayat=["4:29", "39:53", "12:87"], hadith=[("bukhari", 5671)], crisis=True,
         guide_en="Your life is precious to Allah, and this pain can change. Please talk to someone right now: call "
                  "Tele-MANAS on 14416 (free, 24 hours, India) or emergency 112, or tell a family member or friend you "
                  "trust. The Prophet ﷺ taught us never to wish for death because of hardship, but to ask Allah for what "
                  "is best for us.",
         guide_ur="آپ کی زندگی اللہ کے نزدیک قیمتی ہے اور یہ تکلیف بدل سکتی ہے۔ ابھی کسی سے بات کریں: ٹیلی مانس 14416 (مفت، 24 "
                  "گھنٹے) یا ایمرجنسی 112 پر کال کریں، یا کسی بھروسے والے کو بتائیں۔"),
]
