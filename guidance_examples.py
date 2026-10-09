"""Example questions for each "Ask the Quran" topic: the ways people really ask, in English, Roman Urdu
(with common spellings) and Urdu. The matcher compares a visitor's question with these, word by word and by
spelling-tolerant word shapes, so more and more varied examples make it understand more questions.
Add a line whenever someone asks something that doesn't match."""

EXAMPLES = {
    "anxiety": """I feel anxious about my future | I am always worried | I can't stop overthinking | I am so stressed
        | panic attacks | I can't sleep because of worry | what if something bad happens | my mind never rests
        | mujhe bohot tension hai | dil ghabrata hai | bohot pareshan hun | dimagh mein soch chalti rehti hai
        | neend nahi aati fikar se | dar lagta hai har waqt | مجھے بہت پریشانی ہے | دل گھبراتا ہے | فکر سے نیند نہیں آتی""",
    "sadness": """I feel sad all the time | I am depressed | nothing makes me happy | I feel empty inside | I cry every night
        | my heart is broken | I feel low | dil udaas hai | mann nahi lagta | bohot dukhi hun | rona aata hai
        | dil toot gaya | koi khushi nahi | میں بہت اداس ہوں | دل ٹوٹ گیا | رونا آتا ہے""",
    "anger": """I get angry very quickly | how to control my anger | I shout at people | I lose my temper
        | I hit things when angry | mujhe gussa bohot aata hai | gusa control nahi hota | jaldi naraz ho jata hun
        | chillata hun sab pe | ghussa kaise khatam karun | مجھے بہت غصہ آتا ہے | غصہ کیسے قابو کروں""",
    "patience": """life is so hard | everything is going wrong | I am being tested | how to be patient
        | why do bad things happen to me | I am tired of struggling | sabr kaise karun | zindagi bohot mushkil hai
        | sab ulta ho raha hai | musibat pe musibat | azmaish kab khatam hogi | صبر کیسے کروں | زندگی بہت مشکل ہے""",
    "illness": """I am sick | I have cancer | my child is ill | I am in pain | the doctors can't cure me | I am in hospital
        | main bimar hun | bimari theek nahi ho rahi | dard bohot hai | ammi bimar hain | shifa ki dua
        | میں بیمار ہوں | شفا کی دعا | بیماری ٹھیک نہیں ہو رہی""",
    "grief": """my mother died | my father passed away | I lost my child | how to cope with the death of a loved one
        | someone I love died | meri ammi ka inteqal ho gaya | abbu fot ho gaye | ammi guzar gayi | bhai mar gaya
        | kisi apne ki maut ka gham | میری والدہ فوت ہو گئیں | والد کا انتقال ہو گیا""",
    "parents": """my parents don't understand me | I fight with my mother | how to treat my parents | my father is strict
        | my parents are old | ammi abbu se jhagra | walidain ki khidmat | ammi naraz hain | abbu baat nahi sunte
        | والدین سے جھگڑا | ماں باپ کی خدمت""",
    "marriage": """problems with my husband | my wife and I always fight | I want a divorce | my marriage is unhappy
        | how to choose a spouse | rishta nahi mil raha | shohar se jhagra | biwi se larai | shadi kab hogi
        | talaq ka soch raha hun | میاں بیوی کا جھگڑا | شادی کب ہوگی | رشتہ نہیں مل رہا""",
    "children": """my children don't listen | how to raise good kids | I can't have children | my son is going astray
        | bacche baat nahi mante | aulad nahi ho rahi | beta bigar gaya | bachon ki tarbiyat | اولاد نہیں ہو رہی
        | بچوں کی تربیت""",
    "rizq": """I lost my job | I have no money | I am in debt | I can't pay my bills | business is failing
        | how to get more rizq | naukri chali gayi | paise nahi hain | karza bohot hai | rozi ki tangi | kaam nahi mil raha
        | job nahi milti | نوکری نہیں مل رہی | قرض بہت ہے | پیسے نہیں ہیں""",
    "study": """I failed my exam | I am scared of exams | I can't concentrate on study | my results are bad
        | dua for exams | imtihan mein fail ho gaya | parhai mein dil nahi lagta | paper hai kal | result kharab aaya
        | number kam aaye | امتحان میں فیل ہو گیا | پڑھائی میں دل نہیں لگتا""",
    "sin": """I committed a big sin | will Allah forgive me | I keep repeating the same sin | I feel guilty
        | how to repent | maine bohot gunah kiye | kya Allah maaf karega | tauba kaise karun | gunah chhot nahi raha
        | sharminda hun | کیا اللہ مجھے معاف کرے گا | توبہ کیسے کروں | kya Allah mujh se naraz hai | is Allah angry with me | Allah naraz to nahi""",
    "forgive": """someone hurt me badly | I can't forgive my friend | how to let go of a grudge | I want revenge
        | my friend betrayed me | kisi ne dil dukhaya | maaf nahi kar pa raha | badla lena chahta hun | dhoka diya
        | کسی نے دل دکھایا | معاف نہیں کر پا رہا""",
    "lonely": """I am lonely | I have no friends | nobody cares about me | I feel alone | nobody understands me
        | main akela hun | koi saath nahi | kisi ko meri parwah nahi | tanhai | میں اکیلا ہوں | کوئی ساتھ نہیں""",
    "gratitude": """I am never satisfied | others have more than me | how to be grateful | I always compare myself
        | shukar kaise karun | sab ke paas mujh se zyada hai | qanaat nahi hai | شکر کیسے کروں""",
    "envy": """I am jealous of my friend | I envy other people's success | why does he have everything
        | mujhe hasad hota hai | dusron ko dekh ke jalan hoti hai | مجھے حسد ہوتا ہے""",
    "honesty": """I lied to my parents | I lie a lot | is it ok to lie | someone lied to me | I cheated in an exam
        | maine jhoot bola | jhoot bolna chahiye kya | sach bolna mushkil hai | میں نے جھوٹ بولا""",
    "future": """what should I do with my life | I can't decide my career | I am confused about my future
        | should I take this job | what if I fail | career ka faisla | kya karun samajh nahi aata | mustaqbil ki fikar
        | konsa rasta chunun | کیا کروں سمجھ نہیں آتا | مستقبل کی فکر""",
    "prayer": """I don't feel like praying | I keep missing fajr | how to be regular in salah | my iman is weak
        | I feel far from Allah | namaz nahi parhi jati | fajr nahi uthta | iman kamzor hai | namaz mein dil nahi lagta
        | نماز نہیں پڑھی جاتی | ایمان کمزور ہے""",
    "friends": """my friends are a bad influence | I don't have good friends | peer pressure | toxic friends
        | dost galat hain | buri sohbat | achay dost nahi | برے دوست""",
    "pride": """I think I am better than others | I am arrogant | people say I have ego | ghamand | takabbur
        | mujhe ghuroor hai | میں مغرور ہوں""",
    "backbiting": """I talk behind people's back | people gossip about me | is gossip a sin | gheebat karna
        | log meri burai karte hain | chugli | غیبت | لوگ میری برائی کرتے ہیں""",
    "neighbours": """my neighbour troubles me | how to treat neighbours | being kind to people | padosi tang karta hai
        | hamsaye se jhagra | پڑوسی تنگ کرتا ہے""",
    "oppression": """someone is being unfair to me | I am being bullied | my boss treats me badly | I was cheated
        | injustice | mere saath zulm ho raha hai | na insafi | koi tang karta hai | میرے ساتھ ظلم ہو رہا ہے""",
    "hope": """I have lost all hope | there is no way out | I want to give up | nothing will ever change
        | umeed khatam ho gayi | koi rasta nahi | mayoos hun | himmat haar gaya | امید ختم ہو گئی | مایوس ہوں""",
    "dunya": """what is the purpose of life | why are we here | what happens after death | is this world everything
        | I fear death | zindagi ka maqsad kya hai | marne ke baad kya hoga | akhirat | maut ka dar | زندگی کا مقصد
        | مرنے کے بعد کیا ہوگا | dunya fani hai | this world is temporary | duniya ki mohabbat | دنیا فانی ہے""",
    "desire": """I can't control my desires | I watch haram things | I am addicted to porn | how to stay away from zina
        | I keep falling into temptation | nafs pe qaboo nahi | haram cheezein dekhta hun | buri aadat | نفس پر قابو نہیں | how to stop watching bad videos | gande videos dekhta hun | bad habits online | ganday khayalat""",
    "charity": """should I give charity | I am stingy | how much zakat | does sadaqah increase wealth | sadqa kaise dun
        | kanjoosi | zakat kitni hai | صدقہ | زکوٰۃ کتنی ہے""",
    "time": """I waste my time | I am lazy | I procrastinate | I spend all day on my phone | waqt zaya karta hun
        | susti bohot hai | sara din mobile | وقت ضائع کرتا ہوں | سستی بہت ہے""",
    "character": """how to improve my character | I am rude to people | how to have good manners | akhlaq kaise behtar karun
        | log kehte hain main badtameez hun | اخلاق کیسے بہتر کروں""",
    "family": """my family is fighting | my brother doesn't talk to me | problems with in-laws | relatives cut me off
        | bhai se jhagra | rishtedar baat nahi karte | saas bahu ka jhagra | sasural wale tang karte hain
        | بھائی سے جھگڑا | رشتہ دار بات نہیں کرتے""",
    "intention": """I do good deeds to show off | is my intention right | I want people to praise me | niyat saaf nahi
        | dikhawa | ریاکاری | نیت""",
    "qiyamah": """when will the world end | when is the day of judgement | is the end of the world near
        | what are the signs of qiyamah | when will the hour come | duniya kab khatam hogi | duniya kab ktm hogi
        | qayamat kab aayegi | qiyamat kab hogi | kya qayamat qareeb hai | qayamat ki nishaniyan | ye dunya kab tak hai
        | قیامت کب آئے گی | دنیا کب ختم ہوگی | قیامت کی نشانیاں""",
    "dua": """my dua is not accepted | why doesn't Allah answer my prayers | Allah is not listening to me
        | I have been asking for years | does Allah hear me | meri dua qabool nahi hoti | Allah meri kyun nahi sunta
        | dua qubool kab hogi | itni duaen ki | میری دعا قبول نہیں ہوتی | اللہ میری کیوں نہیں سنتا""",
    "crisis": """I want to die | I want to kill myself | I don't want to live anymore | life is not worth living
        | main mar jana chahta hun | khudkushi | zindagi khatam karna chahta hun | جینا نہیں چاہتا""",
}
