(globalThis.TURBOPACK||(globalThis.TURBOPACK=[])).push(["object"==typeof document?document.currentScript:void 0,97012,e=>{"use strict";var t=e.i(43476),o=e.i(33623),i=e.i(71645),a=e.i(90072),l=e.i(8560);let n={square:0,circle:1,triangle:2,diamond:3},r=`
void main() {
  gl_Position = vec4(position, 1.0);
}
`,f=`
precision highp float;

uniform vec3  uColor;
uniform vec2  uResolution;
uniform float uTime;
uniform float uPixelSize;
uniform float uScale;
uniform float uDensity;
uniform float uPixelJitter;
uniform int   uEnableRipples;
uniform float uRippleSpeed;
uniform float uRippleThickness;
uniform float uRippleIntensity;
uniform float uEdgeFade;

uniform int   uShapeType;
const int SHAPE_SQUARE   = 0;
const int SHAPE_CIRCLE   = 1;
const int SHAPE_TRIANGLE = 2;
const int SHAPE_DIAMOND  = 3;

const int   MAX_CLICKS = 10;

uniform vec2  uClickPos  [MAX_CLICKS];
uniform float uClickTimes[MAX_CLICKS];

out vec4 fragColor;

float Bayer2(vec2 a) {
  a = floor(a);
  return fract(a.x / 2. + a.y * a.y * .75);
}
#define Bayer4(a) (Bayer2(.5*(a))*0.25 + Bayer2(a))
#define Bayer8(a) (Bayer4(.5*(a))*0.25 + Bayer2(a))

#define FBM_OCTAVES     5
#define FBM_LACUNARITY  1.25
#define FBM_GAIN        1.0

float hash11(float n){ return fract(sin(n)*43758.5453); }

float vnoise(vec3 p){
  vec3 ip = floor(p);
  vec3 fp = fract(p);
  float n000 = hash11(dot(ip + vec3(0.0,0.0,0.0), vec3(1.0,57.0,113.0)));
  float n100 = hash11(dot(ip + vec3(1.0,0.0,0.0), vec3(1.0,57.0,113.0)));
  float n010 = hash11(dot(ip + vec3(0.0,1.0,0.0), vec3(1.0,57.0,113.0)));
  float n110 = hash11(dot(ip + vec3(1.0,1.0,0.0), vec3(1.0,57.0,113.0)));
  float n001 = hash11(dot(ip + vec3(0.0,0.0,1.0), vec3(1.0,57.0,113.0)));
  float n101 = hash11(dot(ip + vec3(1.0,0.0,1.0), vec3(1.0,57.0,113.0)));
  float n011 = hash11(dot(ip + vec3(0.0,1.0,1.0), vec3(1.0,57.0,113.0)));
  float n111 = hash11(dot(ip + vec3(1.0,1.0,1.0), vec3(1.0,57.0,113.0)));
  vec3 w = fp*fp*fp*(fp*(fp*6.0-15.0)+10.0);
  float x00 = mix(n000, n100, w.x);
  float x10 = mix(n010, n110, w.x);
  float x01 = mix(n001, n101, w.x);
  float x11 = mix(n011, n111, w.x);
  float y0  = mix(x00, x10, w.y);
  float y1  = mix(x01, x11, w.y);
  return mix(y0, y1, w.z) * 2.0 - 1.0;
}

float fbm2(vec2 uv, float t){
  vec3 p = vec3(uv * uScale, t);
  float amp = 1.0;
  float freq = 1.0;
  float sum = 1.0;
  for (int i = 0; i < FBM_OCTAVES; ++i){
    sum  += amp * vnoise(p * freq);
    freq *= FBM_LACUNARITY;
    amp  *= FBM_GAIN;
  }
  return sum * 0.5 + 0.5;
}

float maskCircle(vec2 p, float cov){
  float r = sqrt(cov) * .25;
  float d = length(p - 0.5) - r;
  float aa = 0.5 * fwidth(d);
  return cov * (1.0 - smoothstep(-aa, aa, d * 2.0));
}

float maskTriangle(vec2 p, vec2 id, float cov){
  bool flip = mod(id.x + id.y, 2.0) > 0.5;
  if (flip) p.x = 1.0 - p.x;
  float r = sqrt(cov);
  float d  = p.y - r*(1.0 - p.x);
  float aa = fwidth(d);
  return cov * clamp(0.5 - d/aa, 0.0, 1.0);
}

float maskDiamond(vec2 p, float cov){
  float r = sqrt(cov) * 0.564;
  return step(abs(p.x - 0.49) + abs(p.y - 0.49), r);
}

void main(){
  float pixelSize = uPixelSize;
  vec2 fragCoord = gl_FragCoord.xy - uResolution * .5;
  float aspectRatio = uResolution.x / uResolution.y;

  vec2 pixelId = floor(fragCoord / pixelSize);
  vec2 pixelUV = fract(fragCoord / pixelSize);

  float cellPixelSize = 8.0 * pixelSize;
  vec2 cellId = floor(fragCoord / cellPixelSize);
  vec2 cellCoord = cellId * cellPixelSize;
  vec2 uv = cellCoord / uResolution * vec2(aspectRatio, 1.0);

  float base = fbm2(uv, uTime * 0.05);
  base = base * 0.5 - 0.65;

  float feed = base + (uDensity - 0.5) * 0.3;

  float speed     = uRippleSpeed;
  float thickness = uRippleThickness;
  const float dampT     = 1.0;
  const float dampR     = 10.0;

  if (uEnableRipples == 1) {
    for (int i = 0; i < MAX_CLICKS; ++i){
      vec2 pos = uClickPos[i];
      if (pos.x < 0.0) continue;
      float cellPixelSize = 8.0 * pixelSize;
      vec2 cuv = (((pos - uResolution * .5 - cellPixelSize * .5) / (uResolution))) * vec2(aspectRatio, 1.0);
      float t = max(uTime - uClickTimes[i], 0.0);
      float r = distance(uv, cuv);
      float waveR = speed * t;
      float ring  = exp(-pow((r - waveR) / thickness, 2.0));
      float atten = exp(-dampT * t) * exp(-dampR * r);
      feed = max(feed, ring * atten * uRippleIntensity);
    }
  }

  float bayer = Bayer8(fragCoord / uPixelSize) - 0.5;
  float bw = step(0.5, feed + bayer);

  float h = fract(sin(dot(floor(fragCoord / uPixelSize), vec2(127.1, 311.7))) * 43758.5453);
  float jitterScale = 1.0 + (h - 0.5) * uPixelJitter;
  float coverage = bw * jitterScale;
  float M;
  if      (uShapeType == SHAPE_CIRCLE)   M = maskCircle (pixelUV, coverage);
  else if (uShapeType == SHAPE_TRIANGLE) M = maskTriangle(pixelUV, pixelId, coverage);
  else if (uShapeType == SHAPE_DIAMOND)  M = maskDiamond(pixelUV, coverage);
  else                                   M = coverage;

  if (uEdgeFade > 0.0) {
    vec2 norm = gl_FragCoord.xy / uResolution;
    float edge = min(min(norm.x, norm.y), min(1.0 - norm.x, 1.0 - norm.y));
    float fade = smoothstep(0.0, uEdgeFade, edge);
    M *= fade;
  }

  vec3 color = uColor;

  // sRGB gamma correction - convert linear to sRGB for accurate color output
  vec3 srgbColor = mix(
    color * 12.92,
    1.055 * pow(color, vec3(1.0 / 2.4)) - 0.055,
    step(0.0031308, color)
  );

  fragColor = vec4(srgbColor, M);
}
`;function u({variant:e="square",pixelSize:u=3,color:s="#B497CF",className:c,antialias:d=!0,patternScale:m=2,patternDensity:p=1,liquid:h=!1,liquidStrength:x=.1,liquidRadius:g=1,pixelSizeJitter:w=0,enableRipples:y=!0,rippleIntensityScale:C=1,rippleThickness:S=.1,rippleSpeed:R=.3,liquidWobbleSpeed:T=4.5,autoPauseOffscreen:E=!0,speed:P=.5,transparent:A=!0,edgeFade:b=.5,noiseAmount:M=0,maxFps:I=30,maxDpr:F=1}){let k=(0,i.useRef)(null);return(0,i.useEffect)(()=>{let t,i,c=k.current;if(!c)return;let z=window.matchMedia("(prefers-reduced-motion: reduce)").matches,B=!E,L=document.createElement("canvas"),_=new l.WebGLRenderer({canvas:L,antialias:d,alpha:!0,powerPreference:"high-performance"});_.domElement.style.width="100%",_.domElement.style.height="100%",_.setPixelRatio(Math.min(window.devicePixelRatio||1,F)),c.appendChild(_.domElement),A?_.setClearAlpha(0):_.setClearColor(0,1);let U={uResolution:{value:new a.Vector2(0,0)},uTime:{value:0},uColor:{value:new a.Color(s)},uClickPos:{value:Array.from({length:10},()=>new a.Vector2(-1,-1))},uClickTimes:{value:new Float32Array(10)},uShapeType:{value:n[e]??0},uPixelSize:{value:u*_.getPixelRatio()},uScale:{value:m},uDensity:{value:p},uPixelJitter:{value:w},uEnableRipples:{value:+!!y},uRippleSpeed:{value:R},uRippleThickness:{value:S},uRippleIntensity:{value:C},uEdgeFade:{value:b}},q=new a.Scene,D=new a.OrthographicCamera(-1,1,1,-1,0,1),O=new a.ShaderMaterial({vertexShader:r,fragmentShader:f,uniforms:U,transparent:!0,depthTest:!1,depthWrite:!1,glslVersion:a.GLSL3}),N=new a.PlaneGeometry(2,2);q.add(new a.Mesh(N,O));let G=new a.Clock,V=1e3*Math.random(),H=[];if(h){var X,K;let e;(i=(()=>{let e=document.createElement("canvas");e.width=64,e.height=64;let t=e.getContext("2d");if(!t)throw Error("2D context not available");t.fillStyle="black",t.fillRect(0,0,e.width,e.height);let o=new a.Texture(e);o.minFilter=a.LinearFilter,o.magFilter=a.LinearFilter,o.generateMipmaps=!1;let i=[],l=null,n=6.4,r=e=>{let o={x:64*e.x,y:(1-e.y)*64},i=1;if(e.age<19.2)i=Math.sin(e.age/19.2*Math.PI/2);else{let t;i=-(t=1-(e.age-19.2)/44.8)*(t-2)||0}i*=e.force;let a=`${(e.vx+1)/2*255}, ${(e.vy+1)/2*255}, ${255*i}`;t.shadowOffsetX=320,t.shadowOffsetY=320,t.shadowBlur=n,t.shadowColor=`rgba(${a},${.22*i})`,t.beginPath(),t.fillStyle="rgba(255,0,0,1)",t.arc(o.x-320,o.y-320,n,0,2*Math.PI),t.fill()};return{canvas:e,texture:o,addTouch:e=>{let t=0,o=0,a=0;if(l){let i=e.x-l.x,n=e.y-l.y;if(0===i&&0===n)return;let r=i*i+n*n,f=Math.sqrt(r);o=i/(f||1),a=n/(f||1),t=Math.min(1e4*r,1)}l={x:e.x,y:e.y},i.push({x:e.x,y:e.y,age:0,force:t,vx:o,vy:a})},update:()=>{t.fillStyle="black",t.fillRect(0,0,e.width,e.height);for(let e=i.length-1;e>=0;e--){let t=i[e],o=.015625*t.force*(1-t.age/64);t.x+=t.vx*o,t.y+=t.vy*o,t.age++,t.age>64&&i.splice(e,1)}for(let e=0;e<i.length;e++)r(i[e]);o.needsUpdate=!0},set radiusScale(v){n=6.4*v},get radiusScale(){return n/6.4},size:64}})()).radiusScale=g,(t=new o.EffectComposer(_)).addPass(new o.RenderPass(q,D));let l=(X=i.texture,K={strength:x,freq:T},e=`
    uniform sampler2D uTexture;
    uniform float uStrength;
    uniform float uTime;
    uniform float uFreq;

    void mainUv(inout vec2 uv) {
      vec4 tex = texture2D(uTexture, uv);
      float vx = tex.r * 2.0 - 1.0;
      float vy = tex.g * 2.0 - 1.0;
      float intensity = tex.b;

      float wave = 0.5 + 0.5 * sin(uTime * uFreq + intensity * 6.2831853);

      float amt = uStrength * intensity * wave;

      uv += vec2(vx, vy) * amt;
    }
    `,new o.Effect("LiquidEffect",e,{uniforms:new Map([["uTexture",new a.Uniform(X)],["uStrength",new a.Uniform(K?.strength??.025)],["uTime",new a.Uniform(0)],["uFreq",new a.Uniform(K?.freq??4.5)]])}));H.push(l);let n=new o.EffectPass(D,l);n.renderToScreen=!0,t.addPass(n)}if(M>0){t||(t=new o.EffectComposer(_)).addPass(new o.RenderPass(q,D));let e=new o.Effect("NoiseEffect","uniform float uTime; uniform float uAmount; float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453);} void mainUv(inout vec2 uv){} void mainImage(const in vec4 inputColor,const in vec2 uv,out vec4 outputColor){ float n=hash(floor(uv*vec2(1920.0,1080.0))+floor(uTime*60.0)); float g=(n-0.5)*uAmount; outputColor=inputColor+vec4(vec3(g),0.0);} ",{uniforms:new Map([["uTime",new a.Uniform(0)],["uAmount",new a.Uniform(M)]])});for(let o of(H.push(e),t.passes))o.renderToScreen=!1;let i=new o.EffectPass(D,e);i.renderToScreen=!0,t.addPass(i)}let Y=()=>{for(let e of(U.uTime.value=V+G.getElapsedTime()*P,H)){let t=e.uniforms.get("uTime");t&&(t.value=U.uTime.value)}t?(i?.update(),t.render()):_.render(q,D)},$=()=>{let e=c.clientWidth||1,o=c.clientHeight||1;t?t.setSize(e,o,!1):_.setSize(e,o,!1),U.uResolution.value.set(_.domElement.width,_.domElement.height),U.uPixelSize.value=u*_.getPixelRatio(),z&&Y()};$();let j=new ResizeObserver($);j.observe(c);let J=e=>{let t=_.domElement.getBoundingClientRect();if(e.clientX<t.left||e.clientX>t.right||e.clientY<t.top||e.clientY>t.bottom)return null;let o=_.domElement.width/t.width,i=_.domElement.height/t.height;return{fx:(e.clientX-t.left)*o,fy:(t.height-(e.clientY-t.top))*i,w:_.domElement.width,h:_.domElement.height}},W=0,Q=e=>{let t=J(e);if(!t)return;let{fx:o,fy:i}=t;U.uClickPos.value[W].set(o,i),U.uClickTimes.value[W]=U.uTime.value,W=(W+1)%10},Z=e=>{if(!i)return;let t=J(e);if(!t)return;let{fx:o,fy:a,w:l,h:n}=t;i.addTouch({x:o/l,y:a/n})};window.addEventListener("pointerdown",Q,{passive:!0}),window.addEventListener("pointermove",Z,{passive:!0});let ee=0,et=0,eo=1e3/I,ei=e=>{if(ee=requestAnimationFrame(ei),!B)return;let t=e-et;t<eo-1||(et=e-(t>=eo?t%eo:0),Y())},ea=new IntersectionObserver(([e])=>{B=!!e?.isIntersecting});return E&&ea.observe(c),z?Y():ee=requestAnimationFrame(ei),()=>{cancelAnimationFrame(ee),j.disconnect(),ea.disconnect(),window.removeEventListener("pointerdown",Q),window.removeEventListener("pointermove",Z),N.dispose(),O.dispose(),i?.texture.dispose(),t?.dispose(),_.dispose(),_.forceContextLoss(),_.domElement.remove()}},[d,E,s,b,y,h,g,x,T,F,I,M,p,m,u,w,C,R,S,P,A,e]),(0,t.jsx)("div",{"aria-hidden":"true",className:`relative size-full overflow-hidden ${c??""}`,ref:k})}e.s(["default",()=>u])},64718,e=>{e.n(e.i(97012))}]);