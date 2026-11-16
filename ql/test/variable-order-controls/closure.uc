function emit(v) { print(v, "\n"); }
let x = 'outer';
{
  function before() { emit(x); }
  let x = 'inner';
  function after() { emit(x); }
  before(); after();
}
emit(x);
