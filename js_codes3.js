const companies = $input.first().json.company;
const websites = $input.first().json.website;

const result = [];

// Zaten gönderilmiş veya pas geçilecek tüm şirketlerin listesi
const pasGecilecekSirketler = [
  "3Y TEKNOLOJİ YAZILIM DONANIM BİLİŞİM ELEKTRONİK DANIŞMANLIK EĞİTİM SANAYİ VE TİCARET LİMİTED ŞİRKETİ",
  "3Y TEKNOLOJİ YAZILIM DONANIM BİLİŞİM ELEKTRONİK DANIŞMANLIK EĞİTİM SANAYİ VE TİCARET LİMİTED ŞİRKETİ3Y TEKNOLOJİ YAZILIM DONANIM BİLİŞİM ELEKTRONİK DANIŞMANLIK EĞİTİM SANAYİ VE TİCARET LİMİTED ŞİRKETİ",
  "AEON GAME OYUN STÜDYO YAZILIM VE ANİMASYON ANONİM ŞİRKETİ",
  "AEROMS MÜHENDİSLİK DANIŞMANLIK YAZILIM HİZMETLERİ SAN. VE TİC. A.Ş.",
  "AEROTİM MÜHENDİSLİK YAZILIM VE DANIŞMANLIK SANAYİ TİCARET LİMİTED ŞİRKETİ",
  "Agcurate Bilgi Teknolojileri Anonim Şirketi",
  "AGE BİLGİ SİSTEM OTOMASYON FAALİYETLERİ SANAYİ VE TİCARET LİMİTED ŞİRKETİ",
  "AINTSOFT BİLİŞİM TEKNOLOJİLERİ DANIŞMANLIK TİCARET LİMİTED ŞİRKETİ",
  "Aksöz Makina Sanayi Ticaret Limited Şirketi",
  "AMP YAZILIM SANAYİ VE TİCARET LİMİTED ŞİRKETİ ANKARA ŞUBESİ",
  "ANKAREF İNOVASYON VE TEKNOLOJİ ANONİM ŞİRKETİ",
  "ANKETEK ELEKTRONİK TEKNOLOJİ TİCARET VE SANAYİ LİMİTED ŞİRKETİ",
  "ANOVA ARGE TEKNOLOJİLERİ SANAYİ VE TİCARET ANONİM ŞİRKETİ",
  "ARDİC ARAŞTIRMA GELİŞTİRME LTD. ŞTİ.",
  "Arduvaz Mühendislik Sanayi ve Ticaret Limited Şirketi",
  "ARF BİLGİ TEKNOLOJİLERİ YAZILIM EĞİTİM VE DANIŞMANLIK HİZMETLERİ TİCARET LİMİTED ŞİRKETİ",
  "ARGEDOR BİLİŞİM TEKNOLOJİLERİ SANAYİ VE TİCARET A.Ş.",
  "ARGOSAİ TEKNOLOJİ ANONİM ŞİRKETİ",
  "ARLENTUS KONTROL ELEKTRONİK ELEKTRİK BİLG. YAZ. SAN. TİC. A.Ş.",
  "ARMAKOM BİLİŞİM TEKNOLOJİLERİ A.Ş.",
  "Arpanet Bilişim Teknolojileri Anonim Şirketi",
  "ARVENTO MOBİL SİSTEMLER A.Ş.",
  "Asis Elektronik ve Bilişim Sistemleri A.Ş.",
  "AURVİS BİLİŞİM YAZILIM DANIŞMANLIK ARAŞTIRMA GELİŞTİRME TİCARET LİMİTED ŞİRKETİ",
  "AVEZ ELEKTRONİK İLETİŞİM EĞİTİM DANIŞMANLIĞI TİCARET ANONİM ŞİRKETİ",
  "AYDIN YAZILIM VE ELEKTRONİK SANAYİ ANONİM ŞİRKETİ",
  "Backpack Games Yazılım Anonim Şirketi"
];

// Türkçe karakterleri standart harflere çeviren ve boşluk/noktalama işaretlerini silen temizlik fonksiyonu
function temizle(metin) {
  if (!metin) return "";
  let str = metin.toString().toLowerCase();
  
  // Türkçe karakter dönüşümleri
  const charMap = {
    'ç': 'c', 'ğ': 'g', 'ı': 'i', 'i': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
    'â': 'a', 'î': 'i', 'û': 'u'
  };
  
  str = str.split('').map(char => charMap[char] || char).join('');
  
  // Noktalama işaretlerini, satır sonlarını ve tüm boşlukları temizle
  return str.replace(/[\s\n\r\t.,\/#!$%\^&\*;:{}=\-_`~()]/g, "").trim();
}

// Pas geçileceklerin temizlenmiş hallerini önbelleğe alalım
const temizPasGecilecekler = pasGecilecekSirketler.map(s => temizle(s));

for (let i = 0; i < companies.length; i++) {
  // İlk 340 şirketi tamamen es geçmek için index kontrolü (0'dan başladığı için < 340)
  if (i < 340) {
    continue;
  }

  const company = (companies[i] || "").trim();
  let website = (websites[i] || "").trim();

  if (!company) continue;

  const temizMevcutSirket = temizle(company);

  // Listede veya pas geçilecekler listesinde eşleşme var mı kontrolü
  const zatenPasGecilmeli = temizPasGecilecekler.some(pasGecilen => 
    temizMevcutSirket.includes(pasGecilen) || pasGecilen.includes(temizMevcutSirket)
  );

  if (zatenPasGecilmeli) {
    continue;
  }

  if (
    website &&
    !website.startsWith("http://") &&
    !website.startsWith("https://")
  ) {
    website = "https://" + website;
  }

  result.push({
    json: {
      companyName: company,
      website: website
    }
  });
}

return result;


//#####################################################

// Giriş verisinden html'i güvenli bir şekilde alalım
const html = $json.data || "";

// Regex ile mail adreslerini bulalım
const emails = html.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [];

return [
  {
    json: {
      // Önceki düğümlerden gelen tüm verileri (companyName, website vb.) koruyoruz
      ...$json, 
      // Bulunan e-postaları dizi olarak ekliyoruz
      emails: emails
    }
  }
];



//#####################################################



// n8n'in o anki Loop Over Items döngüsündeki aktif elemanın web sitesini çekiyoruz.
let baseUrl = "";
try {
  baseUrl = $('Loop Over Items').item.json.website || "";
} catch (e) {
  baseUrl = $json.website || "";
}

const companyName = $('Loop Over Items').item.json.companyName || "";

if (baseUrl.endsWith('/')) {
  baseUrl = baseUrl.slice(0, -1);
}

if (baseUrl && !baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
  baseUrl = 'https://' + baseUrl;
}

// Olası iletişim sayfaları
const paths = [
  "/iletisim",
  "/contact",
  "/contact-us",
  "/hakkimizda",
  "/about",
  "/about-us",
  "/kariyer",
  "/career"
];

// N8N'in HTTP Request düğümünün her bir URL'yi aynı anda 
// ayrı birer istek olarak atabilmesi için 8 elemanlı bir liste dönüyoruz.
return paths.map(path => {
  return {
    json: {
      url: baseUrl + path,
      companyName: companyName,
      website: baseUrl
    }
  };
});







//#####################################################






let allEmails = [];
let companyName = "";
let website = "";

// Gelen 8 farklı sayfa isteğinin yanıtlarını tek tek geziyoruz
for (const item of $input.all()) {
  const html = item.json.data || "";
  
  // Şirket bilgilerini yedekleyelim
  if (!companyName) companyName = item.json.companyName;
  if (!website) website = item.json.website;

  // Regex ile mail adreslerini arıyoruz
  const emails = html.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [];
  
  if (emails.length > 0) {
    allEmails = allEmails.concat(emails);
  }
}

// Aynı olan mailleri temizleyelim (Unique hale getirelim)
const uniqueEmails = [...new Set(allEmails)];

return [
  {
    json: {
      companyName: companyName,
      website: website,
      emails: uniqueEmails,
      source: uniqueEmails.length > 0 ? "Contact Pages" : "Not Found"
    }
  }
];




//#####################################################



// 1. OpenAI'dan gelen metni güvenli bir şekilde çekelim
let rawText = "";
try {
    // Alternatif n8n çıktı formatlarını kontrol ederek metni yakalıyoruz
    rawText = $input.first().json.text || 
              $input.first().json.output?.[0]?.content?.[0]?.text || 
              $input.first().json.message?.content || "";
} catch (e) {
    rawText = "";
}

// 2. Yapay zekanın koyduğu gereksiz ```json ve ``` tırnak işaretlerini temizliyoruz
let cleanText = rawText.replace(/```json/gi, "").replace(/```/g, "").trim();

let mailData = { subject: "", body: "" };

// 3. JSON'a dönüştürmeyi deniyoruz
try {
    mailData = JSON.parse(cleanText);
} catch (e) {
    // Eğer yapay zeka düz metin ürettiyse veya JSON kırıldıysa, tüm metni body'ye kurtarma planı:
    mailData.subject = "Yazılım ve Mühendislik Pozisyonları Hk.";
    mailData.body = cleanText;
}

// 4. Bir önceki döngü verisinden şirket bilgilerini çekiyoruz
// Not: Döngü içinde en kararlı çalışan metot $g() veya direkt bağlı girdiyi okumaktır.
const companyEmail = $('Code in JavaScript1').item.json.email;
const companyName = $('Code in JavaScript1').item.json.company_name;

return [{
    json: {
        company_name: companyName,
        to_email: companyEmail,
        subject: mailData.subject || "Yazılım ve Mühendislik Pozisyonları Hk.",
        body: mailData.body
    }
}];
