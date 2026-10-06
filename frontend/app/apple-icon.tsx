import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    <div style={{
      width:"100%",height:"100%",display:"flex",alignItems:"center",justifyContent:"center",
      background:"#020914",borderRadius:38
    }}>
      <div style={{
        width:112,height:112,display:"flex",alignItems:"center",justifyContent:"center",
        border:"3px solid #00f0ff",borderRadius:34,background:"#031322",
        boxShadow:"0 0 30px #00f0ff"
      }}>
        <div style={{
          width:76,height:64,display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",
          border:"3px solid #00f0ff",borderRadius:24,background:"#020b12"
        }}>
          <div style={{display:"flex",gap:14}}>
            <div style={{width:12,height:8,borderRadius:8,background:"#ffffff"}} />
            <div style={{width:12,height:8,borderRadius:8,background:"#ffffff"}} />
          </div>
          <div style={{marginTop:10,width:28,height:3,borderRadius:5,background:"#00f0ff"}} />
          <div style={{position:"absolute",marginTop:-78,width:6,height:16,borderRadius:4,background:"#00f0ff"}} />
        </div>
      </div>
    </div>,
    { ...size }
  );
}