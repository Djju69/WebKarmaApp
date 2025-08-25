const express = require("express");
const path = require("path");
const app = express();
function sendUtf8(res, file) {
  res.type('html; charset=utf-8');
  res.sendFile(path.join(__dirname, 'public', file));
}
const PORT = process.env.PORT || 3000;

app.use(express.static(path.join(__dirname, "public"), {
  extensions: ["html"],
  setHeaders: (res, p) => {
    if (p.endsWith(".html")) res.setHeader("Content-Type","text/html; charset=utf-8");
    else if (p.endsWith(".css")) res.setHeader("Content-Type","text/css; charset=utf-8");
    else if (p.endsWith(".js")) res.setHeader("Content-Type","application/javascript; charset=utf-8");
  }
}));

app.get("/",             (req,res)=>res.sendFile(path.join(__dirname,"public","index.html")));
app.get("/cabinet",      (req,res)=>res.sendFile(path.join(__dirname,"public","cabinet.html")));
app.get("/cabinet/cards",(req,res)=>res.sendFile(path.join(__dirname,"public","cabinet-cards.html")));
app.get("/cabinet/qr",   (req,res)=>res.sendFile(path.join(__dirname,"public","cabinet-qr.html")));
app.get("/cabinet/districts",(req,res)=>res.sendFile(path.join(__dirname,"public","cabinet-districts.html")));
app.get("/cabinet/reviews",(req,res)=>res.sendFile(path.join(__dirname,"public","cabinet-reviews.html")));
app.get("/cabinet/analytics",(req,res)=>res.sendFile(path.join(__dirname,"public","cabinet-analytics.html")));
app.get("/cabinet/integrations",(req,res)=>res.sendFile(path.join(__dirname,"public","cabinet-integrations.html")));
app.get("/cabinet/team",(req,res)=>res.sendFile(path.join(__dirname,"public","cabinet-team.html")));
app.get("/cabinet/settings",(req,res)=>res.sendFile(path.join(__dirname,"public","cabinet-settings.html")));
app.get("/cabinet/support",(req,res)=>res.sendFile(path.join(__dirname,"public","cabinet-support.html")));

app.use((req,res)=>res.status(404).type("text").send("Not Found"));
app.listen(PORT, ()=>console.log("Server is running on port", PORT));app.get('/cabinet/cards', (req, res) => {
  res.sendFile(require('path').join(__dirname, 'public', 'cabinet-cards.html'));
});
app.get('/cabinet/qr', (req, res) => {
  res.sendFile(require('path').join(__dirname, 'public', 'cabinet-qr.html'));
});

app.get('/cabinet/districts', (req, res) => {
  const path = require('path');
  sendUtf8(res, '');
});