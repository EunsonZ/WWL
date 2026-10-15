export {};
type R={ok:true;value:number}|{ok:false;error:string};
function unwrap(r:R):number{
    // @ts-expect-error Must narrow before accessing the success-only field.
    const bad:number=r.value;
    void bad;
    if(r.ok)return r.value;
    throw new Error(r.error);
}
void unwrap;
type Item={name?:string};
// @ts-expect-error exactOptionalPropertyTypes: absent is not explicit undefined.
const item:Item={name:undefined};
void item;
const xs:number[]=[];
// @ts-expect-error noUncheckedIndexedAccess: this may be undefined.
const first:number=xs[0];
void first;
