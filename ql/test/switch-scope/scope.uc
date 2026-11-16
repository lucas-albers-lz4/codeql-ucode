function consume(value) { print(value, "\n"); }
function source() { return 'outer'; }
function probe(k) {
  let x = source();
  consume(x);
  switch (k) {
    case 'a':
      consume(x);
      let x = 'switch';
      consume(x);
      switch (k) {
        case 'inner':
          let x = 'nested';
          consume(x);
          break;
      }
      consume(x);
      break;
    case 'b':
      consume(x);
      break;
    default: break;
  }
  consume(x);

  let y = 'outer';
  switch (k) {
    case 'a': let y = 'first'; consume(y); break;
    default: break;
  }
  consume(y);
  switch (k) {
    case 'a': let y = 'second'; consume(y); break;
    default: break;
  }
  consume(y);

  let q = 'outer';
  switch (k) {
    case 'a':
      let q = 'switch';
      {
        let q = 'block';
        consume(q);
      }
      consume(q);
      break;
    default: break;
  }
  consume(q);

  let i = 'outer';
  switch (k) {
    case 'a':
      let i = 'switch';
      for (let i = 0; i < 1; i++) consume(i);
      consume(i);
      break;
    default: break;
  }
  consume(i);
}
probe('a');
