const e="json-path",r=(n,t,a=e)=>{const s=Object.keys(n).length,i=Array.isArray(n)?"array":"object";Object.entries(n).forEach((([e,n],l)=>{let c,o=document.createElement("div"),u=typeof n,d="string"===u?`"${n}"`:n;c="array"===i?`${a}-item`:`${a}-${e.replaceAll("_","-")}`,"array"!==i&&(o.innerHTML+=`<span class="key">"${e}"</span>: `),n&&"object"===u?(u=Array.isArray(n)?"array":"object",o.innerHTML+="array"===u?"[":"{",r(n,o,c),o.innerHTML+="array"===u?"]":"}"):(u="object"===u?"null":u,o.innerHTML+=`<span class="value ${u}">${d}</span>`),o.innerHTML+=l<s-1?",":"",o.classList.add(c),t.appendChild(o)}))},n=(e,r,t=[],a=[],s=[])=>{const i=Array.isArray(e)?"array":"object";return Object.entries(e).forEach((([e,l])=>{const c="array"===i?`${r}-item`:`${r}-${e}`;a.includes(c)||(a.push(c),"array"!==i&&(t.includes(e)&&!s.includes(e)&&s.push(e),t.push(e)),l&&"object"==typeof l&&(s=n(l,c,t,a,s)))})),s},t=(r,n,a=e,s=[],i=[])=>{const l=Array.isArray(r)?"array":"object",c=e=>e.substring(10).replaceAll("-item","").replaceAll("-","_");Object.entries(r).forEach((([e,r])=>{let o,u,d,p=document.createElement("div"),y=typeof r;"array"===l?(o=`${a}-item`,d=c(a)):(o=`${a}-${e.replaceAll("_","-")}`,d=c(o)),s.includes(o)||(s.push(o),"array"!==l&&(p.innerHTML+=`<span class="key">${e}</span>`,i.includes(e)&&d!==e?p.innerHTML+=`=<span class="renamed-key">${d}</span>: `:p.innerHTML+=": "),r&&"object"===y?(y=Array.isArray(r)?"array":"object",p.innerHTML+="array"===y?"List(":"Struct(",t(r,p,o,s,i),p.innerHTML+=")"):(y="object"===y?"null":y,u=((e,r)=>{let n="Unknown";return"boolean"===r?n="Boolean":"null"===r?n="Null":"number"===r?n=Number.isInteger(e)?"Int64":"Float64":"string"===r&&(n="String"),n})(r,y),p.innerHTML+=`<span class="value ${y}">${u}</span>`),p.classList.add(o),n.appendChild(p))}))},a=(e,r)=>{e.querySelectorAll("div").forEach((e=>{e.addEventListener("mouseenter",(e=>{const n=`.${e.target.classList[0]}`;document.querySelectorAll(n).forEach((e=>{e.classList.add("highlighted")})),r.querySelectorAll(n)[0].scrollIntoView({block:"nearest",inline:"center"})})),e.addEventListener("mouseleave",(e=>{document.querySelectorAll(`.${e.target.classList[0]}`).forEach((e=>{e.classList.remove("highlighted")}))}))}))};document.querySelector("#unpack").innerHTML+='\n<textarea\n  id="unpack-json-input"\n  placeholder="paste/edit your JSON content here"\n  rows="3">\n</textarea>\n<div class="unpacked">\n  <div id="unpack-parsed-input"></div>\n  <div id="unpack-rough-schema"></div>\n</div>\n';const s=document.querySelector("#unpack-json-input"),i=document.querySelector("#unpack-parsed-input"),l=document.querySelector("#unpack-rough-schema"),c=c=>{s.classList.remove("error"),i.innerHTML="",l.innerHTML="",((e,n)=>{e&&"object"==typeof e?(n.innerHTML+=Array.isArray(e)?"[":"{",r(e,n),n.innerHTML+=Array.isArray(e)?"]":"}"):r(e,n)})(c,i),t(c,l,e,[],n(c)),a(i,l),a(l,i)};s.addEventListener("keyup",(e=>{try{const e=JSON.parse(s.value);c(e),window.scrollTo(0,window.innerHeight)}catch(e){s.classList.add("error")}})),c({simple_float:1.23,nested_struct:{simple_boolean:!1,string:"foo",null:null,list_in_struct:{floats:[12.3,45600,789e5]},integers:[1,2,3]},list_of_structs:[{integer:1,string:"3",boolean:!0},{integer:2,string:"4",boolean:!1}],string:"bar"});