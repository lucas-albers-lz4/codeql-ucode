function emit(v) { print(v, "\n"); }
let x = 7;
if (true):
  emit(x);
  let x = 8;
  emit(x);
endif
emit(x);
for (let x = 1; x < 2; x++):
  emit(x);
endfor
emit(x);
for (let x in [2]):
  emit(x);
endfor
emit(x);
for (let key, x in { a: 3 }):
  emit(x);
endfor
emit(x);
