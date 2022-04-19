# coding: utf-8

import re
from LAC import LAC
lac = LAC(mode='lac')

date_list = ['年', '年份', '季度', '秒', '分钟', '小时', '天', '周', '月', '月份', '月初', '月底', '个月', '单季度']
money_list = ['元', '万元', '亿元']
financereport_word = ['营业收入', '归母净利润', '实现收入', '毛利率', '融资', '注册资本', '每股派发现金红利', '归母扣非净利润', '每股收益', '净利润', '扣非净利润',
                      '经营性净现金流', 'EPS', '基本每股收益',
                      '营收', '全年净息差', '非利息净收入占比营收', '录得净利润', '扣非后净利润', '归母净利', '扣非归母净利润', '净息差', '扣非后归母净利润', '录得净利', '拟每10股分红']
year_on_year_word = ['同比增长', '同比', '同比+', '净利润同比增长', '同比下降', '转增', '环比+', '环比增长', 'YOY+', '环比下降', '同比增加', '环比-', '同比-', '同比上行', 'A股股息率']
percent_word = ['%', 'pct']


class ReportExtraction(object):
    def __init__(self):
        self.s = ''

    def _max_list(self, li):
        return max(li, key=len, default='')

    def _str_all_index(self, str_,a):
        # 首先输入变量2个，输出list，然后中间构造每次find的起始位置start,start每次都在找到的索引+1，后面还得有终止循环的条件
        index_list=[]
        start=0
        while True:
            x=str_.find(a,start)
            if x>-1:
                start=x+1
                index_list.append(x)
            else:
                break
        return index_list

    # 解决'同比'和'同比+'  or   '归母净利润' 和 '净利润'  索引覆盖问题
    def _str_all_index_new(self, str, li):
        ind_word_map = {}
        for i in range(len(li)):
            ele = li[i]
            ele_index = self._str_all_index(str, ele)
            if len(ele_index) > 0:
                for j in range(len(ele_index)):
                    if ele_index[j] not in ind_word_map:
                        ind_word_map[ele_index[j]] = []
                        ind_word_map[ele_index[j]].append(ele)
                    else:
                        ind_word_map[ele_index[j]].append(ele)
        # 解决'同比'和'同比+'   索引覆盖问题
        _tmp_index_word_res = {}
        for key in ind_word_map:
            value = ind_word_map[key]
            if len(value) > 1:
                for i in range(len(value)):
                    _ele = self._max_list(value)
                    _tmp_index_word_res[key] = _ele
            else:
                _tmp_index_word_res[key] = value[0]
        return _tmp_index_word_res
        # 解决 '归母净利润' 和 '净利润'  索引覆盖问题

    def is_season(self, w):
        if 'Q' in w:
            _ind = w.index('Q')
            if w[_ind + 1] in ('1', '2', '3', '4'):
                return True
        return False

    def _process_later_cover(self, m):
        res = dict(m)
        _delete_key = []        #    # finance_word:  {75: '营业收入', 43: '归母净利润', 107: '归母净利润', 45: '净利润', 109: '净利润', 21: '营收'}    删除m中key为43和45的问题
        for i in m:
            _i_value = m[i]
            for j in m:
                _j_value = m[j]
                if i != j:
                    if (i < j) and (_j_value in _i_value) and ((j-i) == (len(_i_value) - len(_j_value))):
                        if j not in _delete_key:      # 20220402  删除重复项
                            _delete_key.append(j)
        for k in range(len(_delete_key)):
            del res[_delete_key[k]]
        return res

    # 20220414  解决Q4单季度问题
    def _specify_season(self, s1, s2):
        if s1 in ('Q1单', 'Q2单', 'Q3单', 'Q4单') and s2 in ('季度'):
            return True
        return False

    def ner_index_word(self, s):
        s = s.replace(' ', '')
        s4_res = lac.run(s)
        all_len = len(s4_res[1])
        # 日期实体和所在字符串索引
        date_word_list = []
        money_word_list = []
        finance_word_list = []
        year_word_list = []
        percent_word_list = []
        for i in range(all_len):
            if s4_res[1][i] in ('m', 'n', 'TIME'):
                word = s4_res[0][i]
                for _date in range(len(date_list)):
                    if date_list[_date] in word:
                        date_word_list.append(word)
                for _money in range(len(money_list)):
                    if money_list[_money] in word:
                        money_word_list.append(word)
                for _per in range(len(percent_word)):
                    if percent_word[_per] in word:
                        percent_word_list.append(word)
                if self.is_season(word):    # 添加季度词汇
                    date_word_list.append(word)
                if word in ('年报') and str.isdigit(s4_res[0][i-1]) and len(s4_res[0][i-1]) in (2, 4):      # 解决年报的前一个词是数字 对应的日期问题
                    date_word_list.append(s4_res[0][i-1])
            tmp_word = s4_res[0][i]         # 20220402  处理 被lac识别为ORG，但其中有TIME的word     # 1-2月公司   ---   提取出1-2月
            for i in range(len(tmp_word)):
                if i>1 and tmp_word[i] in date_list:
                    tmp_date_word = re.findall(r"[0-9-]", tmp_word[:i])
                    if tmp_date_word != '':
                        date_word_list.append(''.join(tmp_date_word) + tmp_word[i])
        for i in range(all_len):
            if i < all_len - 1:
                _tmp_word = s4_res[0][i]
                _add_tmp_word = s4_res[0][i+1]
                if self._specify_season(_tmp_word, _add_tmp_word):
                    date_word_list.append(_tmp_word + _add_tmp_word)

        for _finance in range(len(financereport_word)):
            if financereport_word[_finance] in s:
                finance_word_list.append(financereport_word[_finance])
        for _year in range(len(year_on_year_word)):
            if year_on_year_word[_year] in s:
                year_word_list.append(year_on_year_word[_year])

        tmp_date_map = self._str_all_index_new(s, date_word_list)
        tmp_money_map = self._str_all_index_new(s, money_word_list)
        tmp_finance_map = self._str_all_index_new(s, finance_word_list)
        tmp_year_map = self._str_all_index_new(s, year_word_list)
        tmp_per_map = self._str_all_index_new(s, percent_word_list)

        res_date_map = self._process_later_cover(tmp_date_map)
        res_money_map = self._process_later_cover(tmp_money_map)
        res_finance_map = self._process_later_cover(tmp_finance_map)
        res_year_map = self._process_later_cover(tmp_year_map)
        res_per_map = self._process_later_cover(tmp_per_map)
        return res_date_map, res_money_map, res_finance_map, res_year_map, res_per_map

    def union_date_list(self, sorted_date_list):
        last_sorted_date_list = []
        #sorted_date_list = [(9, '2022年'), (14, '1-2月'), (22, '2021年')]
        delete_index_list = []
        if len(sorted_date_list) > 1:
            for i in range(len(sorted_date_list) - 1):
                if sorted_date_list[i + 1][0] - sorted_date_list[i][0] == len(sorted_date_list[i][1]):
                    last_sorted_date_list.append(
                        (sorted_date_list[i][0], sorted_date_list[i][1] + sorted_date_list[i + 1][1]))
                    delete_index_list.append(i)
                    delete_index_list.append(i + 1)
            for i in range(len(sorted_date_list)):
                if i not in delete_index_list:
                    last_sorted_date_list.append(sorted_date_list[i])
        else:
            last_sorted_date_list = sorted_date_list
        return last_sorted_date_list

    def list_to_map(self, li):    # list-map   [(9, '2022年1-2月')]   ---   {'9', '2022年1-2月'}
        res = {}
        for i in range(len(li)):
            res[li[i][0]] = li[i][1]
        return res

    def less_min_list_ele(self, li, ele):
        _min = 99999
        for i in li:
            if i < ele:
                if ele - i < _min:
                    _min = ele - i
        return abs(ele - _min)

    def above_min_list_ele(self, li, ele):       #   [26, 39, 53, 65, 81, 94]    22
        _min = 99999
        for i in li:
            if i > ele and (i - ele) < _min:
                _min = i - ele
        return ele + _min

    def union_twolist_tomap3(self, li1, li2):
        li1_ind = [key[0] for key in li1]
        li2_ind = [key[0] for key in li2]
        li1_len = len(li1)
        li2_len = len(li2)
        res = {}
        if li1_ind[0] > li2_ind[0]:       #   [28, 54],   [26, 49, 75, 86]
            if li1_len < li2_len:
                tmp_li2 = []
                for i in range(li1_len):
                    _min = self.less_min_list_ele(li2_ind, li1_ind[i])
                    for j in range(li2_len):
                        if _min == li2_ind[j]:
                            tmp_li2.append(li2_ind[j])
                            res[li2_ind[j]] = li2[j][1] + '_' + li1[i][1]
                for k in range(li2_len):
                    if li2_ind[k] not in tmp_li2:
                        res[li2_ind[k]] = li2[k][1]
            elif li1_len > li2_len:       #    [28, 54, 88]  [26, 44]
                tmp_li1 = []
                for i in range(li2_len):
                    _max = self.above_min_list_ele(li1_ind, li2_ind[i])
                    for j in range(li1_len):
                        if _max == li1_ind[j]:
                            tmp_li1.append(li1_ind[j])
                            res[li2_ind[i]] = li2[i][1] + '_' + li1[j][1]
                for k in range(li1_len):
                    if li1_ind[k] not in tmp_li1:
                        res[li1_ind[k]] = li1[k][1]
            else:
                #  [(16, '690.1亿元'), (39, '37.2亿元'), (117, '154.8亿元'), (138, '4.1亿元'), (166, '6.87元')]      [(14, '营收'), (34, '录得净利润'), (56, '扣非后净利润'), (115, '营收'), (134, '录得净利')]
                tmp_li1, tmp_li2 = [], []
                for i in range(li2_len):
                    for j in range(li1_len):
                        if li2_ind[i] + len(li2[i][1]) == li1_ind[j]:
                            res[li2_ind[i]] = li2[i][1] + '_' + li1[j][1]
                            tmp_li1.append(li1_ind[j])
                            tmp_li2.append(li2_ind[i])
                for i in range(li1_len):
                    if li1_ind[i] not in tmp_li1:
                        res[li1_ind[i]] = li1[i][1]
                for i in range(li2_len):
                    if li2_ind[i] not in tmp_li2:
                        res[li2_ind[i]] = li2[i][1]
        else:   #    li1[0][0]  <  li2[0][0]
            if li1_len < li2_len:
                tmp_li2 = []
                for i in range(li1_len):
                    _max = self.above_min_list_ele(li2_ind, li1_ind[i])      #   42
                    for j in range(li2_len):
                        if _max == li2_ind[j]:
                            tmp_li2.append(li2_ind[j])
                            res[li1_ind[i]] = li1[i][1] + '_' + li2[j][1]
                for k in range(li2_len):
                    if li2_ind[k] not in tmp_li2:
                        res[li2_ind[k]] = li2[k][1]
            elif li1_len > li2_len:          #   [38, 64, 103],    [42, 68]
                tmp_li1 = []
                for i in range(li2_len):
                    _min = self.less_min_list_ele(li1_ind, li2_ind[i])
                    print('_min: ', _min)
                    for j in range(li2_len):
                        if _min == li1_ind[j]:
                            tmp_li1.append(li1_ind[j])
                            res[li1_ind[j]] = li1[j][1] + '_' + li2[i][1]
                for k in range(li1_len):
                    if li1_ind[k] not in tmp_li1:
                        res[li1_ind[k]] = li1[k][1]
            else:
                tmp_li1, tmp_li2 = [], []
                for i in range(li1_len):
                    for j in range(li2_len):
                        if li1_ind[i] + len(li1[i][1]) == li2_ind[j]:
                            res[li1_ind[i]] = li1[i][1] + '_' + li2[j][1]
                            tmp_li1.append(li1_ind[i])
                            tmp_li2.append(li2_ind[j])
                for i in range(li1_len):
                    if li1_ind[i] not in tmp_li1:
                        res[li1_ind[i]] = li1[i][1]
                for i in range(li2_len):
                    if li2_ind[i] not in tmp_li2:
                        res[li2_ind[i]] = li2[i][1]
        return res

    def main(self, s):
        res_date_map, res_money_map, res_finance_map, res_year_map, res_per_map = self.ner_index_word(s)
        sorted_date_list = sorted(res_date_map.items(), key=lambda x:x[0], reverse=False)
        sorted_money_list = sorted(res_money_map.items(), key=lambda x:x[0], reverse=False)
        sorted_finance_list = sorted(res_finance_map.items(), key=lambda x:x[0], reverse=False)
        sorted_year_list = sorted(res_year_map.items(), key=lambda x:x[0], reverse=False)
        sorted_per_list = sorted(res_per_map.items(), key=lambda x:x[0], reverse=False)

        # 合并时间
        sorted_date_list = self.union_date_list(sorted_date_list)
        res_date_map = self.list_to_map(sorted_date_list)

        # 20220408  15:25   存在sorted_finance_list和sorted_money_list长度不一致的问题
        finance_money = self.union_twolist_tomap3(sorted_finance_list, sorted_money_list)
        year_per = self.union_twolist_tomap3(sorted_year_list, sorted_per_list)
        finance_money_key_list = [key for key in finance_money]

        # 营收-金额-增长率-百分比
        finance_money_union_year_per = {}
        for key in year_per:
            tmp_ind = self.less_min_list_ele(finance_money_key_list, key)       #    31 ---> 21
            for i in finance_money:
                if tmp_ind == i:
                    if tmp_ind not in finance_money_union_year_per:
                        finance_money_union_year_per[tmp_ind] = finance_money[i] + '_' + year_per[key]
                    else:
                        finance_money_union_year_per[tmp_ind] = finance_money_union_year_per[tmp_ind]  + '_' + year_per[key]
                # 20220408 11:36  解决finance_money中的key不在结果map中的问题
                if i not in finance_money_union_year_per:
                    finance_money_union_year_per[i] = finance_money[i]
        # 年份-营收-金额-增长率-百分比
        date_list = [key for key in res_date_map]
        date_all_event = {}
        for key in finance_money_union_year_per:
            tmp_ind = self.less_min_list_ele(date_list, key)
            for i in res_date_map:
                if tmp_ind == i:
                    if tmp_ind not in date_all_event:
                        date_all_event[tmp_ind] = res_date_map[i] + '_' + finance_money_union_year_per[key]
                    else:
                        date_all_event[tmp_ind] = date_all_event[tmp_ind] + '_' + finance_money_union_year_per[key]

        date_all_event_list = []
        for key in finance_money_union_year_per:
            tmp_ind = self.less_min_list_ele(date_list, key)
            for i in res_date_map:
                if tmp_ind == i:
                    date_all_event_list.append(res_date_map[i] + '_' + finance_money_union_year_per[key])
        return date_all_event_list

    def _main(self):
        s1 = '事件：公司发布2021年报，21年全年实现营收87.13亿元，同比+39.18%；实现归母净利润21.20亿元，同比增加30.15%。其中单四季度实现营业收入23.76亿元，环比+2.89%，同比+5.89%。实现归母净利润4.03亿元，环比-11.57%，同比-50.67%，业绩符合预期。'
        res = self.main(s1)
        print(res)

if __name__ == '__main__':
    reportExtraction = ReportExtraction()
    reportExtraction._main()
