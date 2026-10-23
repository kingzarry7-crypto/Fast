#property strict
#property version   "1.00"
#property description "Kitty JustMarkets bridge - shadow only, never places orders"
input string BridgeBaseUrl = "https://YOUR-RAILWAY-HOST";
input string BridgeToken = "";
input string ExpectedServer = "";
input long AllowedAccountLogin = 0;
input int PollSeconds = 30;
input string BrokerSymbolBTC = "BTC";
input string BrokerSymbolGold = "XAUUSD";
bool g_verified=false;
string TrimSlash(string s){ while(StringLen(s)>0 && StringSubstr(s,StringLen(s)-1,1)=="/") s=StringSubstr(s,0,StringLen(s)-1); return s; }
string JsonEscape(string s){ StringReplace(s,"\\","\\\\"); StringReplace(s,"\"","\\\""); return s; }
bool IsDemo(){ return AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_DEMO; }
bool IdentityOK(){ return IsDemo() && ExpectedServer!="" && AccountInfoString(ACCOUNT_SERVER)==ExpectedServer && AllowedAccountLogin>0 && AccountInfoInteger(ACCOUNT_LOGIN)==AllowedAccountLogin; }
string SymbolObject(string name){
 if(!SymbolSelect(name,true)) return "";
 long mode=0,digits=0,stops=0;
 double vmin=0,vmax=0,vstep=0,tick=0,tickval=0;
 if(!SymbolInfoInteger(name,SYMBOL_TRADE_MODE,mode) || !SymbolInfoInteger(name,SYMBOL_DIGITS,digits) || !SymbolInfoInteger(name,SYMBOL_TRADE_STOPS_LEVEL,stops)) return "";
 if(!SymbolInfoDouble(name,SYMBOL_VOLUME_MIN,vmin) || !SymbolInfoDouble(name,SYMBOL_VOLUME_MAX,vmax) || !SymbolInfoDouble(name,SYMBOL_VOLUME_STEP,vstep) || !SymbolInfoDouble(name,SYMBOL_TRADE_TICK_SIZE,tick) || !SymbolInfoDouble(name,SYMBOL_TRADE_TICK_VALUE,tickval)) return "";
 return "{\"name\":\""+JsonEscape(name)+"\",\"trade_mode\":"+IntegerToString((int)mode)+",\"digits\":"+IntegerToString((int)digits)+",\"stops_level\":"+IntegerToString((int)stops)+",\"volume_min\":"+DoubleToString(vmin,8)+",\"volume_max\":"+DoubleToString(vmax,8)+",\"volume_step\":"+DoubleToString(vstep,8)+",\"tick_size\":"+DoubleToString(tick,8)+",\"tick_value\":"+DoubleToString(tickval,8)+"}";
}
bool Request(string method,string path,string body,string &response){
 if(BridgeToken=="" || StringLen(BridgeToken)<32 || StringFind(BridgeBaseUrl,"https://")!=0) return false;
 string headers="Content-Type: application/json\r\nAuthorization: Bearer "+BridgeToken+"\r\n";
 char data[],result[]; string response_headers;
 if(StringLen(body)>0) StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);
 else ArrayResize(data,0);
 ResetLastError();
 int code=WebRequest(method,TrimSlash(BridgeBaseUrl)+path,headers,8000,data,result,response_headers);
 if(code<200 || code>=300){ Print("Kitty MT5 bridge HTTP status=",code," error=",GetLastError()); return false; }
 response=CharArrayToString(result,0,-1,CP_UTF8);
 return true;
}
string ExtractString(string json,string key){
 string marker="\""+key+"\""; int p=StringFind(json,marker); if(p<0)return "";
 p=StringFind(json,":",p+StringLen(marker)); if(p<0)return ""; p++;
 while(p<StringLen(json) && (StringGetCharacter(json,p)==' ' || StringGetCharacter(json,p)=='\"')) p++;
 int end=StringFind(json,"\"",p); if(end<0)return "";
 return StringSubstr(json,p,end-p);
}
void SendHeartbeat(){
 bool identity=IdentityOK();
 string syms="";
 if(identity){ string a=SymbolObject(BrokerSymbolBTC); string b=SymbolObject(BrokerSymbolGold); if(a!="")syms=a; if(b!=""){if(syms!="")syms+=",";syms+=b;} }
 string body="{\"terminal_connected\":"+string(TerminalInfoInteger(TERMINAL_CONNECTED)?"true":"false")+",\"trade_mode\":\""+string(IsDemo()?"DEMO":"OTHER")+"\",\"server\":\""+JsonEscape(AccountInfoString(ACCOUNT_SERVER))+"\",\"account_id\":\""+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"\",\"symbols\":["+syms+"]}";
 string response;
 if(Request("POST","/justmarkets-mt5/heartbeat",body,response)){ g_verified=identity && StringFind(response,"\"demo_verified\":true")>=0; }
 else g_verified=false;
 if(!g_verified) Print("Kitty MT5 bridge blocked: demo/server/account identity not verified.");
}
void PollWork(){
 if(!g_verified || !IdentityOK()) return;
 string response;
 if(!Request("GET","/justmarkets-mt5/work","",response))return;
 if(StringFind(response,"\"work\":null")>=0 || StringFind(response,"\"work\": null")>=0)return;
 string id=ExtractString(response,"signal_id"),symbol=ExtractString(response,"symbol"),direction=ExtractString(response,"direction");
 if(id=="" || (symbol!=BrokerSymbolBTC && symbol!=BrokerSymbolGold) || (direction!="BUY" && direction!="SELL"))return;
 // Shadow only: report that this signal was evaluated. No CTrade/order API is imported or called.
 string body="{\"signal_id\":\""+JsonEscape(id)+"\",\"status\":\"shadow_evaluated\",\"code\":\"SHADOW_ONLY\",\"reason\":\"Signal reviewed; no broker order submitted\"}";
 string ackResponse; Request("POST","/justmarkets-mt5/ack",body,ackResponse);
 Print("SHADOW ONLY: ",symbol," ",direction," signal=",id,". No order submitted.");
}
int OnInit(){
 if(BridgeToken=="" || StringLen(BridgeToken)<32 || ExpectedServer=="" || AllowedAccountLogin<=0 || PollSeconds<10){ Print("Configuration invalid; EA stopped."); return INIT_PARAMETERS_INCORRECT; }
 if(!EventSetTimer(PollSeconds)){ Print("Timer initialization failed."); return INIT_FAILED; }
 SendHeartbeat(); return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){ EventKillTimer(); }
void OnTimer(){ SendHeartbeat(); PollWork(); }
