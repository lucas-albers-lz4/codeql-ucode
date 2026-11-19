import { popen } from 'fs';
function local_shadow() {
  const fd = popen('printf harmless');
  {
    const fd = { read: function(x) { return x; }, close: function() {} };
    fd.read('all');
    fd.close();
  }
  fd.read('all');
  fd.close();
}
