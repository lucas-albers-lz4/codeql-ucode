import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      let command;
      command = `echo ${input.args.value} done`;
      for (let command in ['echo constant done'])
        return popen(command);
    }
  }
};
return { probe: methods };
