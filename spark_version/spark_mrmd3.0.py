#!/usr/bin/env python
# coding: utf-8




import findspark
findspark.init()
import pyspark
import random






from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("MRMD3.0 Spark").getOrCreate()



from sklearn.datasets import make_classification
import pandas as pd
import numpy as np


import networkx as nx
from sklearn.model_selection import RandomizedSearchCV
from sklearn.preprocessing import StandardScaler,MinMaxScaler
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import LinearSVC
from pyspark.sql.types import StructType, StructField, IntegerType, FloatType,ArrayType,StringType
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from pyspark.sql.functions import pandas_udf, struct, PandasUDFType
import sklearn.metrics
import sklearn.model_selection
from sklearn.preprocessing import LabelBinarizer
from sklearn.preprocessing import KBinsDiscretizer
from operator import itemgetter
from minepy import MINE
from sklearn.feature_selection import RFE
from sklearn import metrics
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import MinMaxScaler
from sklearn.neighbors import KNeighborsClassifier
import re
import json
import ast,os
from sklearn.feature_selection import SelectKBest,f_classif
from  feature_rank.trustrank import trustrank
import networkx as nx
from feature_rank.leaderank import  leaderrank
from sklearn.feature_selection import SelectKBest, mutual_info_classif
from sklearn.feature_selection import chi2
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.linear_model import Lasso,LogisticRegression,Ridge
import math
from sklearn.naive_bayes import ComplementNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import GradientBoostingClassifier
import argparse
import time





a = time.time()  #start time
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s","--start", dest='s',type=int, help="start index", default=1)
    parser.add_argument("-i", "--inputfile",dest='i',type=str, help="input file", required=True)
    parser.add_argument("-e","--end", dest='e',type=int, help="end index", default=-1)
    parser.add_argument("-l","--length", dest='l',type=int, help="step length", default=1)
    parser.add_argument("-n","--n_dim",dest='n', type=int, help="mrmd2.0 features top n", default=-1)
    parser.add_argument("-t", "--type_metric",dest='t',type=str, help="evaluation metric", default="f1")
    parser.add_argument("-m", "--metrics_file",dest='m',type=str, help="output the metrics file", default=None)
    parser.add_argument("-o", "--outfile",dest='o',type=str, help="output the dimensionality reduction file")
    parser.add_argument("-p", "--picture",dest='p',type=str,default='false', help="The scatter plots before and after dimension reduction are generated by tsne")
    parser.add_argument("-r", "--rank_method", dest='r', type=str, help="the rank method for features",choices=["PageRank",
                                                                                                                "Hits_a",
                                                                                                                "Hits_h",
                                                                                                                "LeaderRank",
                                                                                                                "TrustRank"],
                                                                                                         default="PageRank")
    parser.add_argument("-c", "--classifier",dest='c',type=str, help="classifier(RandomForest,SVM,Bayes)", default="RandomForest",choices=["RandomForest","SVM","Bayes"])
    args = parser.parse_args()

    return args

args = parse_args()
df = pd.read_csv(args.i)
# X, y = make_classification(n_samples = 1000, n_features = 200, n_classes = 2, weights = [0.5,0.5], random_state = 1)
# X_y = np.append(y.reshape(-1, 1),X, axis = 1)
# df = pd.DataFrame(X_y, columns = ['class']+['x' + str(i) for i in range(200)])

X_columns = df.columns[1:].tolist()
y_label = df.columns[0]


def ANOVA(X,y,features_name):
    
    model1 = SelectKBest(f_classif, k=1)  # 选择k个最佳特征
    model1.fit_transform(X,y)
    result = [(x,y) for x,y in zip(features_name[:],model1.scores_)]

    result = sorted(result, key=lambda x: x[1], reverse=True)
    return [x[0] for x in result]




def MIC(X,y,features_name):
    mic_score = {}
 
    for name in features_name:
        mine = MINE(alpha=0.6, c=15)
        score = mine.compute_score(X[name], y)
        #score = mine.compute_score(X[name].tolist(), y.tolist())
        score = mine.mic()
        mic_score[name]= score
 
    mic_score =[(a,b) for a,b in mic_score.items()]
    mic_score = sorted(mic_score,key = lambda x:x[1],reverse=True)
    mic_features =[x[0] for x in mic_score]
    
    return mic_features


def NMI(X,y,features_name):
    NMI_score = {}
    discretizer = KBinsDiscretizer(
            n_bins=5, encode='ordinal', strategy='uniform')
    
    for name in features_name:
        x = np.array(X[name]).reshape(-1, 1)
        x = discretizer.fit_transform(x)
        x= x.reshape(-1)
        score = metrics.normalized_mutual_info_score(x, y)
        #score = mine.compute_score(X[name].tolist(), y.tolist())
  
        NMI_score[name]= score
 
    NMI_score =[(a,b) for a,b in NMI_score.items()]
    NMI_score = sorted(NMI_score,key = lambda x:x[1],reverse=True)
    NMI_features =[x[0] for x in NMI_score]
    
    return NMI_features





def entropy(x):

    _, count = np.unique(x, return_counts=True, axis=0)
    prob = count/len(x)
    return np.sum((-1) * prob * np.log2(prob))


def joint_rntropy(y, x):

    yx = np.c_[y, x]
    return entropy(yx)


def conditional_entropy(y, x):

    return joint_rntropy(y, x) - entropy(x)


def mutual_information(x, y):

    return (entropy(x) - conditional_entropy(x, y))

class MRMR():


    def __init__(self, n_features=20, k_max=None):
        self.n_features = n_features
        self.k_max = k_max

    @staticmethod
    def _mutual_information_target(X, y):


        mi_vec = []
        for x in X.T:
            mi_vec.append(mutual_information(x, y))

        return sorted(enumerate(mi_vec), key=itemgetter(1), reverse=True)

    def _handle_fit(self, X, y, threshold=0.8):
        """ handler method for fit """

        ndim = X.shape[1]
        if self.k_max:
            k_max = min(ndim, self.k_max)
        else:
            k_max = ndim

        ## TODO: set k_max
        k_max = ndim

        # mutual informaton between feature fectors and target vector
        MI_trg_map = self._mutual_information_target(X, y)

        # subset the data down to k_max
        sorted_MI_idxs = [i[0] for i in MI_trg_map]
        X_subset = X[:, sorted_MI_idxs[0:k_max]]

        # mutual information within feature vectors
        MI_features_map = {}

        # Max-Relevance first feature
        idx0, MaxRel = MI_trg_map[0]

        mrmr_map = [(idx0, MaxRel)]
        idx_mask = [idx0]

        MI_features_map[idx0] = []
        for x in X_subset.T:
            MI_features_map[idx0].append(mutual_information(x, X[:, idx0]))

        for _ in range(min(self.n_features - 1, ndim - 1)):

            # objective func
            phi_vec = []
            for idx, Rel in MI_trg_map[1:k_max]:
                if idx not in idx_mask:
                    Red = sum(MI_features_map[j][idx] for j, _ in mrmr_map) / len(mrmr_map)
                    phi = (Rel - Red)
                    phi_vec.append((idx, phi))

            idx, mrmr_val = max(phi_vec, key=itemgetter(1))

            MI_features_map[idx] = []
            for x in X_subset.T:
                MI_features_map[idx].append(mutual_information(x, X[:, idx]))

            mrmr_map.append((idx, mrmr_val))
            idx_mask.append(idx)

        mrmr_map_sorted = sorted(mrmr_map, key=itemgetter(1), reverse=True)
        return [x[0] for x in mrmr_map_sorted]

    def fit(self, X, y, threshold=0.8):



        x = np.array(X)
        if not 0.0 < threshold < 1.0:
            raise ValueError('threshold value must be between o and 1.')


        discretizer = KBinsDiscretizer(
            n_bins=5, encode='ordinal', strategy='uniform')
        ##read_data
        x = discretizer.fit_transform(x)

        #return self._handle_fit(X, y, threshold)
        return list(df.columns[1:][self._handle_fit(x, y, threshold)])


def mRMR(X,y,features_name):
    mrmr = MRMR(n_features=100)
    return mrmr.fit(X, y, threshold=0.1)


# ### F_value

# In[8]:



def f_value(X,y,features_name):
    model1 = SelectKBest(f_regression, k=1)  # 选择k个最佳特征
    model1.fit_transform(X, y)
    result = [(x, y) for x, y in zip(features_name[:], model1.scores_)]
    result = sorted(result, key=lambda x: x[1], reverse=True)
    return [x[0] for x in result]



def chi2_(X,y,features_name):
    scaler = MinMaxScaler()
    X = scaler.fit_transform(X)
    model1 = SelectKBest(chi2, k=1)  # 选择k个最佳特征
    model1.fit_transform(X, y)
    result = [(x, y) for x, y in zip(features_name[:], model1.scores_)]
    result = sorted(result, key=lambda x: x[1], reverse=True)
    return [x[0] for x in result]




def lasso(X,y,features_name):
    scaler = MinMaxScaler()
    X = scaler.fit_transform(X)

    lasso = Lasso()
    lasso.fit(X, y)
    result = [(x, y) for x, y in zip(features_name[:], lasso.coef_)]

    result = sorted(result, key=lambda x: abs(x[1]), reverse=True)
    
    return [x[0] for x in result]

def ridge(X,y,features_name):
    scaler = MinMaxScaler()
    X = scaler.fit_transform(X)
    
    ridge = Ridge()
    ridge.fit(X, y)
    result = [(x, y) for x, y in zip(features_name[:], ridge.coef_)]
    result = sorted(result, key=lambda x: abs(x[1]), reverse=True)
    return [x[0] for x in result]

def logistic(X,y,features_name):
    scaler = MinMaxScaler()
    X = scaler.fit_transform(X)
    logistic = LogisticRegression()
    logistic.fit(X, y)

    result = [(x, y) for x, y in zip(features_name[:], logistic.coef_[0])]
    result = sorted(result, key=lambda x: abs(x[1]), reverse=True)
    
    return  [x[0] for x in result]



def calcE(X,coli,colj):
    # sum=0
    # for i in range(len(X)):
    #
    #      sum+=(X[i,coli]-X[i,colj])*(X[i,coli]-X[i,colj])
    sum = np.sum((X[:,coli]-X[:,colj])**2)


    return math.sqrt(sum)

def calcT(X,coli,colj):

    numerator =  np.sum(X[:,coli]*X[:,colj])  #分母
    denominator =  np.sqrt(np.sum(X[:,coli]*X[:,coli])) * np.sqrt(np.sum(X[:,colj]*X[:,colj]))  #分子
    if denominator ==0:
        return 0
    return numerator/denominator

def calcC(X,coli,colj):

    numerator =  np.sum(X[:,coli]*X[:,colj])  #分母
    denominator =  np.sum(X[:,coli]*X[:,coli]) * np.sum(X[:,colj]*X[:,colj])-numerator  #分子
    if denominator ==0:
        return 0
    return numerator/denominator

def Tanimoto(X,n):
    tanimotodata = np.zeros([n,n])
    for i in range(n):
        for j in range(n):
            if i==j:
                tanimotodata[i, j]=0
            else:
                tanimotodata[i,j]=calcT(X,i,j)
                tanimotodata[j,i]=tanimotodata[i,j]
    tan_distance = []

    for i in range(n):
        sum = np.sum(tanimotodata[i, :])
        tan_distance.append(sum / n)

    return tan_distance

def Euclidean(X,n):

    Euclideandata=np.zeros([n,n])

    for i in range(n):
        for j in range(n):
            Euclideandata[i,j]=calcE(X,i,j)
            Euclideandata[j,i]=Euclideandata[i,j]

    Euclidean_distance=[]

    for i in range(n):
        sum = np.sum(Euclideandata[i,:])
        Euclidean_distance.append(sum/n)

    return Euclidean_distance

def Cosine(X,n):

    Cosinedata = np.zeros([n,n])
    for i in range(n):
        for j in range(n):
            if i==j:
                Cosinedata[i, j]=0
            else:
                Cosinedata[i,j]=calcC(X,i,j)
                Cosinedata[j,i]=Cosinedata[i,j]
    Cos_distance = []

    for i in range(n):
        sum = np.sum(Cosinedata[i, :])
        Cos_distance.append(sum / n)

    return Cos_distance

def varience(data,avg1,col1,avg2,col2):

    return np.average((data[:,col1]-avg1)*(data[:,col2]-avg2))

def Person(X,y,n):
    feaNum=n
    #label_num=len(y[0,:])
    label_num=1
    PersonData=np.zeros([n])
    for i in range(feaNum):
        for j in range(feaNum,feaNum+label_num):
            #print('. ', end='')
            average1 = np.average(X[:,i])
            average2 = np.average(y)
            yn=(X.shape)[0]
            y=y.reshape((yn,1))
            dataset = np.concatenate((X,y),axis=1)
            numerator = varience(dataset, average1, i, average2, j);
            denominator = math.sqrt(
                varience(dataset, average1, i, average1, i) * varience(dataset, average2, j, average2, j));
            if (abs(denominator) < (1E-10)):
                PersonData[i]=0
            else:
                PersonData[i]=abs(numerator/denominator)

    return list(PersonData)

def  mrmd_c(X,y,features_name):
    X = np.array(X)
    y = np.array(y)
    n=len(features_name)
    c=Cosine(X,n)
    ###cos
    mrmrValue=[]
    p = Person(X,y,n)
    for i,j in zip(p,c):
        mrmrValue.append(i+j)

    mrmr_max=max(mrmrValue)
    mrmrValue = [x / mrmr_max for x in mrmrValue]
    mrmrValue = [(i,j) for i,j in zip(features_name[:],mrmrValue)]   # features 和 mrmrvalue绑定
    mrmd_c=sorted(mrmrValue,key=lambda x:x[1],reverse=True)  #按mrmrValue 由大到小排序
    return [x[0] for x in mrmd_c]

def mrmd_e(X,y,features_name):
    X = np.array(X)
    y = np.array(y)
    n=len(features_name)
    e=Euclidean(X,n)
    ###欧氏距离
    mrmrValue=[]
    p = Person(X,y,n)
    for i,j in zip(p,e):
        mrmrValue.append(i+j)

    mrmr_max=max(mrmrValue)
    mrmrValue = [x / mrmr_max for x in mrmrValue]
    mrmrValue = [(i,j) for i,j in zip(features_name[:],mrmrValue)]   # features 和 mrmrvalue绑定
    mrmd_e=sorted(mrmrValue,key=lambda x:x[1],reverse=True)  #按mrmrValue 由大到小排序
    
    return [x[0] for x in mrmd_e]


def mrmd_t(X,y,features_name):
    X = np.array(X)
    y = np.array(y)
    n=len(features_name)
    t=Tanimoto(X,n)
    p = Person(X,y,n)
        ##tan
    mrmrValue=[]
    for i,j in zip(p,t):
        mrmrValue.append(i+j)

    mrmr_max=max(mrmrValue)
    mrmrValue = [x / mrmr_max for x in mrmrValue]
    mrmrValue = [(i,j) for i,j in zip(features_name[:],mrmrValue)]   # features 和 mrmrvalue绑定
    mrmd_t=sorted(mrmrValue,key=lambda x:x[1],reverse=True)  #按mrmrValue 由大到小排序
    
    return [x[0] for x in mrmd_t]



def MI(X,y,features_name):
    np.random.seed(1)
    scaler = MinMaxScaler()
    X = scaler.fit_transform(X)
    model1 = SelectKBest(mutual_info_classif, k=1)  # 选择k个最佳特征
    model1.fit_transform(X, y)
    result = [(x, y) for x, y in zip(features_name[:], model1.scores_)]
    result = sorted(result, key=lambda x: x[1], reverse=True)
    return [x[0] for x in result]



def tree_Fimportance1(X,y,features_name):


    rf = RandomForestClassifier(random_state=1)
    rf.fit(X, y)
    lis1 = rf.feature_importances_


    result1 = [(x, y) for x, y in zip(features_name[:], lis1)]
    result1 = sorted(result1, key=lambda x: x[1], reverse=True)

    return [x[0] for x in result1]


def tree_Fimportance2(X,y,features_name):

    dt = DecisionTreeClassifier(random_state=1)
    dt.fit(X, y)
    lis2 = dt.feature_importances_

    result2 = [(x, y) for x, y in zip(features_name[:], lis2)]
    result2 = sorted(result2, key=lambda x: x[1], reverse=True)

    return  [x[0] for x in result2]
  

def tree_Fimportance3(X,y,features_name):

    gb = GradientBoostingClassifier(random_state=1)
    gb.fit(X, y)
    lis3 = gb.feature_importances_

    result3 = [(x, y) for x, y in zip(features_name[:], lis3)]
    result3 = sorted(result3, key=lambda x: x[1], reverse=True)

    return  [x[0] for x in result3]





def ref1(X,y,features_name):
    estimator = LinearSVC(random_state=1)
    selector = RFE(estimator=estimator, n_features_to_select=1)
    selector.fit_transform(X, y)
    result1 = sorted(zip(map(lambda x: round(x, 4), selector.ranking_), features_name[:]))
    return [x[1] for x in result1]

def ref2(X,y,features_name):
    estimator = LogisticRegression(random_state=1)
    selector = RFE(estimator=estimator, n_features_to_select=1)
    selector.fit_transform(X, y)
    result2 = sorted(zip(map(lambda x: round(x, 4), selector.ranking_), features_name[:]))
    return [x[1] for x in result2]

def ref3(X,y,features_name):
    estimator = RandomForestClassifier(random_state=1)
    selector = RFE(estimator=estimator, n_features_to_select=1)
    selector.fit_transform(X, y)
    result3 = sorted(zip(map(lambda x: round(x, 4), selector.ranking_), features_name[:]))
    return [x[1] for x in result3]

def ref4(X,y,features_name):
    estimator =  GradientBoostingClassifier(random_state=1)
    selector = RFE(estimator=estimator, n_features_to_select=1)
    selector.fit_transform(X, y)
    result4 = sorted(zip(map(lambda x: round(x, 4), selector.ranking_), features_name[:]))
    return [x[1] for x in result4]


def ref5(X,y,features_name):
    estimator = ComplementNB()
    selector = RFE(estimator=estimator, n_features_to_select=1)
    MinMax = MinMaxScaler()
    X = MinMax.fit_transform(X)
    selector.fit_transform(X, y)
    result5 = sorted(zip(map(lambda x: round(x, 4), selector.ranking_), features_name[:]))
    return [x[1] for x in result5]


funcs=[ANOVA,MIC,MI,NMI,mRMR,f_value,chi2_,lasso,ridge,logistic,mrmd_c,mrmd_e,mrmd_t,tree_Fimportance1,tree_Fimportance2,tree_Fimportance3,ref1,ref2,ref3,ref4,ref5]
index2funcs = {i:func for i,func in enumerate(funcs)}
df_feature_rank_index = pd.DataFrame({ 'feature_method':[x for x in range(len(funcs))]})
#print(index2funcs)
df_feature_rank_index





df_feature_rank_index_spark = spark.createDataFrame(df_feature_rank_index)
# df_feature_rank_index_spark.count() #21
df_feature_rank_index_spark.show()




schema = StructType([
#     StructField('id', IntegerType()),
#     StructField('len', IntegerType()),
#     #StructField('feature_score_list', ArrayType(elementType=FloatType())),
#     StructField('df.id.unique', StringType()),
    StructField('func_name', StringType()),
    StructField('feature_score_list', StringType()),
])


X_columns = df.drop(columns = [y_label]).columns
y_columns = y_label

@pandas_udf(schema, PandasUDFType.GROUPED_MAP)
def model_results_per_id(df1):

    X = df[X_columns]
    y = df[y_columns]
    result = index2funcs[df1.feature_method[0]](X,y,X_columns)
    
    result = str(result)
    model_results = pd.DataFrame([[index2funcs[df1.feature_method[0]].__name__,result]], columns = ['func_name', 'feature_score_list'])
    return model_results





model_results_by_id = df_feature_rank_index_spark.groupBy('feature_method').apply(model_results_per_id).toPandas()





feature_selection_methods_result = []
for x in  model_results_by_id.feature_score_list.tolist():
    feature_selection_methods_result.append(ast.literal_eval(x))

# for id,x in  enumerate(feature_selection_methods_result):  #特征选择方法
#     print(id,x)





def node2edge(nodeOrder_des):  #特征 大-》小
    edges=[]
    for onetype_featureSelection in nodeOrder_des:
        edges +=[(onetype_featureSelection[i+1],onetype_featureSelection[i]) for  i,x in enumerate(onetype_featureSelection) if i<len(onetype_featureSelection)-1]
    ###去重
    #edges = [elem for elem in edges if elem not in edges]
    edges = sorted(set(edges), key=lambda x: edges.index(x))
    return  edges

edges=node2edge(feature_selection_methods_result)
G = nx.DiGraph()
G.add_edges_from(edges)




def webpage_rank(features,graph,method,edges):
    if method.lower() == "pagerank":
        pr = nx.pagerank(graph)
        return sorted(pr.items(),key=lambda x: x[1], reverse=True)
    elif method.lower() == "hits_a":
        h, a = nx.hits(graph)
        return sorted(a.items(), key=lambda x: x[1], reverse=True)
    elif method.lower() == "hits_h":
        h, a = nx.hits(graph)
        return sorted(h.items(), key=lambda x: x[1], reverse=True)
    elif method.lower() == "leaderrank":
        lr = leaderrank(graph)
        #print("leaderrank+++++++++++",lr.items())
        return sorted(lr.items(), key=lambda item: item[1], reverse=True)
    else:   ###trustrank
        tr = trustrank(features,edges)
        return sorted(tr.items(), key=lambda item: item[1], reverse=True)



features = {}
i = 1

for x in X_columns:
    features[x] = i
    i += 1
features_rc = features.copy()

rank_method = args.r
rankresultWithsocre = webpage_rank(features, graph=G,method=rank_method,edges=edges)
#print("rankresultWithsocre",rankresultWithsocre)
print("The final  rank is")
for value in rankresultWithsocre:
    print(str(value[0])+ " : "+str(value[1]))
    
#print('features',features_rc)

feature_rank_result = [x[0] for x in rankresultWithsocre if str(x[0]!='0')]

feature_rank_result


# ### 构建交叉验证的数据集



feature_cv_order1 = []
feature_cv_order2 = []
feature_rank_result
for elem in feature_rank_result:
    #print(elem)
    feature_cv_order1.append(elem)
    feature_cv_order2.append(list(feature_cv_order1))

df_cv = pd.DataFrame({ 'feature_rd_list': feature_cv_order2}).reset_index()





schema = StructType([
    StructField('index', StringType()),
    StructField('f1', FloatType()),
    StructField('precision', FloatType()),
    StructField('recall', FloatType()),
    StructField('acc', FloatType()),
    StructField('auc', FloatType())
    #StructField('feature_list', StringType())
])
#final_df = final_df.iloc[0:100,:]

if args.c == "SVM":
    clf =  LinearSVC(random_state=1, tol=1e-5)
elif args.c == "Bayes":
    clf = GaussianNB()
else:
    clf = RandomForestClassifier(random_state=1, n_estimators=100)

@pandas_udf(schema, PandasUDFType.GROUPED_MAP)
def CV_model_results_per_index(df1):
#     id = int(df.id.unique()[0])
    X_columns = list(df1.feature_rd_list[0])
    y_columns= y_label
    X = df[X_columns]
    y = df[y_columns]
    
    ypred = sklearn.model_selection.cross_val_predict(clf, X, y, n_jobs=-1, cv=5)
    f1 = sklearn.metrics.f1_score(y, ypred, average='weighted')
    precision = sklearn.metrics.precision_score(y, ypred, average='weighted')
    recall = sklearn.metrics.recall_score(y, ypred, average='weighted')
    acc = sklearn.metrics.accuracy_score(y, ypred)
    lb = LabelBinarizer()
    lb.fit(y)

    y = lb.transform(y)
    ypred = lb.transform(ypred)
    auc = sklearn.metrics.roc_auc_score(y, ypred)
    
    
    model_results = pd.DataFrame([[str(list(df1.feature_rd_list[0])),f1,precision,recall,acc,auc]], columns = ['index','f1','precision','recall','acc','auc'])
    return model_results





feature_CV_df_spark = spark.createDataFrame(df_cv)
res = feature_CV_df_spark.groupBy('index').apply( CV_model_results_per_index).toPandas()
print(res)




#result = ast.literal_eval(res['index'][res.f1.idxmax()])
result = eval(f"ast.literal_eval(res['index'][res.{args.t}.idxmax()])")
#print(result,res['f1'][res.f1.idxmax()])
print(result,eval(f"res['{args.t}'][res.{args.t}.idxmax()]"))
print(len(result))





label = y_label
df_result = df.loc[:,[label]+result]#.astype({label: int})




ypred = sklearn.model_selection.cross_val_predict(clf, np.array(df.loc[:,[label]+result]), np.array(df.loc[:,[label]]), n_jobs=-1, cv=5)


cm = pd.crosstab(pd.Series(np.array(df[y_label]), name='Actual'), pd.Series(ypred, name='Predicted'))
confusion_matrix = str('***confusion matrix***' + os.linesep + str(cm))
print(confusion_matrix)
df_result.to_csv(args.i+'.out',index=None)
print(f'Reduced dimensional dataset has been saved in the {args.i}.out')
print("time=",time.time()-a)
