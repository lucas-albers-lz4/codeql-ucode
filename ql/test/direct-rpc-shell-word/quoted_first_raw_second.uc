import { popen } from 'fs';
function shellquote(v) { return `'${replace(v, "'", "'\\''")}'`; }
const methods = {
  probe: {
    call: function(input) {
      return popen(`echo ${shellquote(input.args.prefix)} ${input.args.value} done`);
    }
  }
};
return { probe: methods };
