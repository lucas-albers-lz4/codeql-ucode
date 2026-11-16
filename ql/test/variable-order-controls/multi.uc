function emit(v) { print(v, "\n"); }
let x = 'outer';
{
  let other = x, x = 'inner';
  emit(other); emit(x);
}
emit(x);
