function consume(value) { print(value, "\n"); }
function source() { return 'outer'; }
function probe() {
  let x = source();
  {
    consume(x);
    let x = 'inner';
    consume(x);
  }
  consume(x);
}
probe();

function formal(x) {
  consume(x);
  {
    consume(x);
    let x = 'inner';
    consume(x);
  }
  consume(x);
}
function loop(x) {
  for (let x in [1]) {
    consume(x);
  }
  consume(x);
}
function catching(x) {
  try { fail(1); }
  catch (x) { consume(x); }
  consume(x);
}
function nested(x) {
  {
    function inner() { consume(x); }
    let x = 'later';
    inner();
  }
  consume(x);
}
function unresolved() {
  consume(x);
  let x = 1;
  consume(x);
}
function sameline(x) { { consume(x); let x = 'inner'; consume(x); } consume(x); }
