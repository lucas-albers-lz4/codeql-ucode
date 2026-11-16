function source() { return 'outer'; }
function probe(k) {
  let x = source();
  for (;;) {
    switch (k) { default: break; }
    x = 'safe';
    break;
  }
  print(x, "\n");
}
probe('a');
