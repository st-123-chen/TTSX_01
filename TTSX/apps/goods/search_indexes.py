# 定义索引类
from haystack import indexes
# 导入模型类
from ..goods.models import GoodsSKU


# 指导对于某个了的某些数据建立索引
# 索引类名格式：模型类名+Index
class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    # 索引字段 use_template指导根据表中的哪些字段建立索引文件，把说明放在一个文件中
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        # 返回你的模型类
        return GoodsSKU

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
