import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      let command;
      if (input.args.use) {
        command = `echo ${input.args.value} done`;
      } else {
        return popen(command);
      }
    }
  }
};
return { probe: methods };
