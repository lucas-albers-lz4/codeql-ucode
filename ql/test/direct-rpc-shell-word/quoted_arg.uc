import { popen } from 'fs';
function shellquote(v) { return `'${replace(v, "'", "'\\''")}'`; }
const methods = {
  probe: {
    call: function(payload) {
      return popen(`echo ${shellquote(payload.args.value)} done`);
    }
  }
};
return { probe: methods };
