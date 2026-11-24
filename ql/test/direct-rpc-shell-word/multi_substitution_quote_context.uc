import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      return popen(`echo ${input.args.prefix} ${input.args.value} done`);
    }
  }
};
return { probe: methods };
