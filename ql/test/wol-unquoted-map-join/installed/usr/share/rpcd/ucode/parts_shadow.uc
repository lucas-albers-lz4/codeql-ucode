import { popen } from 'fs';
function transform(s) { return s; }
const methods = {
  exec: {
    call: function(request) {
      let parts = map(request.args.args, transform);
      if (true) {
      let parts = ['fixed'];
      const fd = popen('/bin/echo' + ' ' + join(' ', parts));
      }
    }
  }
};
return { 'testing.wol': methods };
