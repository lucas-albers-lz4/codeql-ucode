import { stat, readfile } from 'fs';
const base = '/fixture';
const methods = {
  observe: {
    args: { service_name: 'service_name' },
    call: function(request) {
      if (!request.args.service_name) return null;
      {
        let request = { args: { service_name: 'fixture' } };
        return stat(`${base}/${request.args.service_name}.log`);
      }
    }
  }
};
return { 'luci.review.stat': methods };
