function emit(v) { print(v, "\n"); }
function unresolved() { emit(x); let x = 'later'; emit(x); }
function invoke() { helper(); }
function helper() { emit('helper'); }
let x = 'forward-file'; emit(x);
