from elasticsearch import Elasticsearch

class EsBase(object):
    """
    es base
    """
    def __init__(self, index):
        self.es = Elasticsearch(["internal-liveme-data-es-online-878203834.us-east-1.elb.amazonaws.com:9200"], http_auth=('liveme_bigdata_dev', 'rw_GFfZGV2'))
        self.index = index

    @staticmethod
    def parse_query_result(result):
        """
        解析查询的结果
        :param result:
        :return:
        """
        resp = {
            "data": [],
            "total": 0
        }
        if not result or "hits" not in result or not result["hits"]:
            return result
        resp["data"] = result.get("hits", {}).get("hits", {})
        resp["total"] = result.get("hits", {}).get("total", 0)
        return resp

    def query_one(self, query, source, doc_type='online'):
        """
        查找某一条操作
        :param query:
        :return:
        """
        result = self.es.search(index=self.index, doc_type=doc_type, body=query, _source=source)
        return self.parse_query_result(result)

    def insert_one(self, query, doc_type='online'):
        result = self.es.index(index=self.index, doc_type=doc_type, body=query)
        return result

    def insert_one_id(self, query, id, doc_type='online'):
        result = self.es.index(index=self.index, doc_type=doc_type, body=query, id=id)
        return result

    # {'_index': 'liveme_datacenter_ailab_anchor_tag', '_type': 'online', '_id': 'e2uqyngBnvsGnf63E5tq', '_version': 1, 'result': 'created', '_shards': {'total': 2, 'successful': 2, 'failed': 0}, '_seq_no': 0, '_primary_term': 1}

    def update_one_local(self, query, id, doc_type='online'):
        result = self.es.update(index=self.index, doc_type=doc_type, id=id, body=query)
        return result

    def update_one_global(self, query, id, doc_type='online'):
        result = self.es.index(index=self.index, doc_type=doc_type, id=id, body=query)
        return result

    def delete_one(self, id, doc_type='online'):
        result = self.es.delete(index=self.index, doc_type=doc_type, id=id)
        return result


    def search_all(self, query, doc_type='online',size=10):
        result = self.es.search(index=self.index, doc_type=doc_type, body = query,size=size)
#        print(result)
        return self.parse_query_result(result)
    def delete_by_query(self, query, doc_type='online'):
        result = self.es.delete_by_query(index=self.index, body=query, doc_type=doc_type)
        return result

    def count_doc(self, doc_type='online'):
        result = self.es.count(index=self.index, doc_type=doc_type)
        return result

    def get_id(self,id, doc_type = 'online'):
        result = self.es.get(index=self.index, doc_type=doc_type, id=id)
        return result


    def search_all_res(self, query,doc_type='online'):
        query = self.es.search(index=self.index, doc_type=doc_type, body=query, scroll='5m', size=100)
        results = query['hits']['hits']  # es查询出的结果第一页
        total = query['hits']['total']['value']  # es查询出的结果总量
        scroll_id = query['_scroll_id']  # 游标用于输出es查询出的所有结果
        for i in range(0, int(total / 100) + 1):
            # scroll参数必须指定否则会报错
            query_scroll = self.es.scroll(scroll_id=scroll_id, scroll='5m')['hits']['hits']
            results += query_scroll
        resp = {}
        print(len(results),"results")
        resp["data"] = results
        resp["total"] = {"value":total}
        return resp