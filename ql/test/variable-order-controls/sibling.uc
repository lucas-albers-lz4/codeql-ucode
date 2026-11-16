function emit(v) { print(v, "\n"); }
let x = 'outer';
{ let x = 'sibling'; emit(x); }
{ emit(x); const x = 'inner'; emit(x); }
emit(x);
