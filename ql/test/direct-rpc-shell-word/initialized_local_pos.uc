import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      const command = `echo ${input.args.item} done`;
      return popen(command);
    }
  }
};
return { probe: methods };
