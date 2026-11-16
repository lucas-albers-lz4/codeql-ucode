function emit(v) { print(v, "\n"); }
let x = 'outer';
if (true) {
  emit(x);
  let x = 'inner';
  emit(x);
} else {
  emit(x);
  const x = 'sibling';
  emit(x);
}
emit(x);
