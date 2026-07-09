// ====== 1. NODE: Sadece Şirket İsimlerini Çıkaran JavaScript Kodu ======
const html = $input.first().json.data || "";
const tdRegex = /<td>([\s\S]*?)<\/td>/gi;
const result = [];
let match;
let allCells = [];

while ((match = tdRegex.exec(html)) !== null) {
    let cellText = match[1].replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
    if (cellText) { allCells.push(cellText); }
}

for (let i = 0; i < allCells.length; i += 2) {
    let companyName = allCells[i];
    if (companyName && companyName.length > 2 && !companyName.includes("FİRMA ADI")) {
        result.push({ json: { company_name: companyName } });
    }
}
return result;


// ====== 2. NODE: OpenAI Çıktısını Objelere Dönüştüren JavaScript2 Kodu ======
const rawText = $input.first().json.output?.[0]?.content?.[0]?.text || $input.first().json.text || "";
let cleanText = rawText.replace(/```json/gi, "").replace(/```/g, "").trim();
let parsedData = { email: null, subject: "", body: "" };

try {
    parsedData = JSON.parse(cleanText);
} catch (e) {
    const emailMatch = cleanText.match(/"email"\s*:\s*"([^"]+)"/);
    const subjectMatch = cleanText.match(/"subject"\s*:\s*"([^"]+)"/);
    const bodyMatch = cleanText.match(/"body"\s*:\s*"([\s\S]+?)"\s*\n*\s*}/);
    if (emailMatch) parsedData.email = emailMatch[1];
    if (subjectMatch) parsedData.subject = subjectMatch[1];
    if (bodyMatch) parsedData.body = bodyMatch[1];
}

const originalCompanyName = $('Loop Over Items').item.json.company_name || "";
return [{
    json: {
        company_name: originalCompanyName,
        email: parsedData.email,
        subject: parsedData.subject,
        body: parsedData.body
    }
}];
