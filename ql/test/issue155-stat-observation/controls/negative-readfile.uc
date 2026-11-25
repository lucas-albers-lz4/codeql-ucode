import { stat, readfile } from 'fs';
const base = '/fixture';
const methods = {
  observe: {
    args: { service_name: 'service_name' },
    call: function(request) {
      if (!request.args.service_name) return null;
      {
        return readfile(`${base}/${request.args.service_name}.log`);
      }
    }
  }
};
return { 'luci.review.stat': methods };
