function emit(v) { print(v, "\n"); }
let x = 'outer';
{ emit(({ x }).x); let x = 'inner'; emit(({ x }).x); }
emit(x);
