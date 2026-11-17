function source() { return 'outer'; }
function probe(k) {
  let x = source();
  for (;;) {
    switch (k) { case 'a': break; default: print('control'); }
    x = 'safe';
    break;
  }
  print(x, "\n");
}
probe('a');
