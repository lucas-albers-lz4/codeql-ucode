import { popen } from 'fs';
function transform(s) { return s; }
const methods = {
  exec: {
    call: function(request) {
      let transform = function(s) { return 'constant'; };
      let parts = map(request.args.args, transform);
      const fd = popen('/bin/echo' + ' ' + join(' ', parts));
      return fd;
    }
  }
};
return { 'testing.wol': methods };
