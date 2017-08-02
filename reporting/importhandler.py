import logging
import fbapi
import awapi
import twapi
import ttdapi
import szkftp
import os
import datetime as dt
import pandas as pd
import vmcolumns as vmc
import cleaning as cln


class ImportHandler(object):
    def __init__(self, args, matrix):
        self.args = args
        self.matrix = matrix

    def output(self, api_merge, api_df, filename, first_row, last_row, vk):
        cln.dir_check(vmc.pathraw)
        if str(api_merge) != 'nan':
            api_merge_file = vmc.pathraw + str(api_merge)
            if os.path.isfile(api_merge_file):
                try:
                    df = pd.read_csv(api_merge_file, parse_dates=True)
                except IOError:
                    logging.warn(api_merge + ' could not be opened.  ' +
                                 'API data was not merged.')
                    api_df.to_csv(api_merge_file)
                    return None
                df = cln.first_last_adj(df, first_row, last_row)
                df = self.create_all_col(df)
                api_df = cln.first_last_adj(api_df, first_row, last_row)
                api_df = self.create_all_col(api_df)
                api_df = api_df[~api_df['ALL'].isin(df['ALL'])]
                df = df.append(api_df, ignore_index=True)
                df.drop('ALL', axis=1, inplace=True)
                df.to_csv(api_merge_file, index=False)
                if first_row != 0:
                    self.matrix.vm_change(vk, vmc.firstrow, 0)
                if last_row != 0:
                    self.matrix.vm_change(vk, vmc.lastrow, 0)
            else:
                logging.warn(api_merge + ' not found.  Creating file.')
                df = pd.DataFrame()
                df = df.append(api_df, ignore_index=True)
                df.to_csv(api_merge_file, index=False)
        else:
            try:
                api_df.to_csv(vmc.pathraw + filename, index=False)
            except IOError:
                logging.warn(vmc.pathraw + filename + ' could not be ' +
                             'opened.  API data was not saved.')

    @staticmethod
    def create_all_col(df):
        df['ALL'] = ''
        for col in df.columns:
            df['ALL'] = df['ALL'] + df[col].astype(str)
        return df

    def arg_check(self, arg_check):
        if self.args == arg_check or self.args == 'all':
            return True
        else:
            return False

    @staticmethod
    def date_check(date):
        if date.date() is pd.NaT:
            return True
        return False

    def api_calls(self, key_list, api_class):
        for vk in key_list:
            params = self.matrix.vendor_set(vk)
            api_class.input_config(params[vmc.apifile])
            start_check = self.date_check(params[vmc.startdate])
            end_check = self.date_check(params[vmc.enddate])
            if params[vmc.apifields] == ['nan']:
                params[vmc.apifields] = None
            if start_check:
                params[vmc.startdate] = None
            if end_check:
                params[vmc.enddate] = None
            df = api_class.get_data(sd=params[vmc.startdate],
                                    ed=params[vmc.enddate],
                                    fields=params[vmc.apifields])
            self.output(params[vmc.apimerge], df, params[vmc.filename],
                        params[vmc.firstrow], params[vmc.lastrow], vk)

    def api_loop(self):
        if self.arg_check('fb'):
            self.api_calls(self.matrix.api_fb_key, fbapi.FbApi())
        if self.arg_check('aw'):
            self.api_calls(self.matrix.api_aw_key, awapi.AwApi())
        if self.arg_check('tw'):
            self.api_calls(self.matrix.api_tw_key, twapi.TwApi())
        if self.arg_check('ttd'):
            self.api_calls(self.matrix.api_ttd_key, ttdapi.TtdApi())

    def ftp_load(self, ftp_key, ftp_class):
        for vk in ftp_key:
            params = self.matrix.vendor_set(vk)
            ftp_class.input_config(params[vmc.apifile])
            df = ftp_class.get_data()
            self.output(params[vmc.apimerge], df, params[vmc.filename],
                        params[vmc.firstrow], params[vmc.lastrow], vk)

    def ftp_loop(self):
        if self.arg_check('sz'):
            self.ftp_load(self.matrix.ftp_sz_key, szkftp.SzkFtp())
