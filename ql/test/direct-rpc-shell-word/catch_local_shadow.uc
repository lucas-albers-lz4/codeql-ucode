import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      let command;
      command = `echo ${input.args.value} done`;
      try { fail(); }
      catch (command) { return popen(command); }
    }
  }
};
return { probe: methods };
