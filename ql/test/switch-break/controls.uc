function source() { return 'outer'; }
function positive_flow() {
  let x = source();
  print(x);
}
function controls(k, guard) {
  while (guard) {
    switch (k) {
      case 'nested':
        switch (k) { default: break; } // inner_break
        print('after-inner'); // after_inner
        break; // outer_break
      case 'fall':
        print('fallthrough'); // fallthrough
      default: break; // final_break
    }
    print('after-switch'); // after_switch
    continue; // loop_continue
  }
  print('after-loop'); // after_loop
}
function switch_continue(k, guard) {
  while (guard) { // continue_guard
    switch (k) { default: continue; } // switch_continue
    print('unreachable');
  }
}
function loop_break(guard) {
  while (guard) {
    break; // loop_break
  }
  print('loop-exit'); // loop_exit
}
