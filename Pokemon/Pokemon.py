import csv
from matplotlib import colors
import pandas as pd
import sys
sys.path.append('../')
from BayesBackpropagation import *
import math
import torch.optim as optim
import json

def generatePokemonData(NUM_BATCHES):

    data = []
    with open('pokemon.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count != 0:
                r,g,b = colors.to_rgb(row[13])
                if row[3]!="":
                    data.append([row[1],row[13],r,g,b,row[3]])
                    data.append([row[1],row[13],r,g,b,row[2]])
                else:
                    data.append([row[1],row[13],r,g,b,row[2]])
                
            line_count += 1
    data = np.asanyarray(data)[:,1:6]
    data = pd.DataFrame(data)
    data.columns = ['Colour', 'R', 'G','B','Type']
    types = data['Type'].unique()
    pokemonType = {}
    pokemon = {}
    """
    temp = data.groupby(['Colour', 'Type']).size()
    temp = temp.reset_index(level=['Colour','Type'])
    temp = temp.pivot(index='Colour', columns='Type')
    temp.to_csv(r'./DataDistribution.csv')
    """

    for i in range(types.size):
        pokemonType[types[i]] = i
        pokemon[i] = types[i]
    data = data.replace({'Type': pokemonType})
    
    pokemonColors = data['Colour'].unique()
    train_x = data.loc[:,['R', 'G','B']]
    train_y = data.drop(['Colour', 'R', 'G','B'],axis=1)
    
    X = np.array_split(train_x,NUM_BATCHES)
    Y = np.array_split(train_y,NUM_BATCHES)
    
    return  X,Y,pokemon,pokemonColors

def train(net, optimizer, data, target, NUM_BATCHES):
    for i in range(NUM_BATCHES):
        net.zero_grad()
        x = torch.tensor(data[i].values.astype(np.float32))
        y = torch.tensor(target[i].values.astype(np.int)).view(-1)
        loss = net.BBB_loss(x, y)
        loss.backward()
        optimizer.step()

def trainBBB(train_x,train_y,TRAIN_EPOCHS,NUM_BATCHES):
    #Hyperparameter setting
    SAMPLES = 10
    BATCH_SIZE = train_x[0].shape[0]
    CLASSES = 18
    INPUT_SIZE = 3
    PI = 0.5
    SIGMA_1 = torch.FloatTensor([math.exp(-0)])
    SIGMA_2 = torch.FloatTensor([math.exp(-6)])
    if torch.cuda.is_available():
        SIGMA_1 = torch.cuda.FloatTensor([math.exp(-0)])
        SIGMA_2 = torch.cuda.FloatTensor([math.exp(-6)])
 
    #Training
    print('Training Begins!')


    #Declare Network
    net = BayesianNetwork(inputSize = INPUT_SIZE,\
                        CLASSES = CLASSES, \
                        layers=np.array([400,400]), \
                        activations = np.array(['relu','relu','softmax']), \
                        SAMPLES = SAMPLES, \
                        BATCH_SIZE = BATCH_SIZE,\
                        NUM_BATCHES = NUM_BATCHES,\
                        hasScalarMixturePrior = True,\
                        PI = PI,\
                        SIGMA_1 = SIGMA_1,\
                        SIGMA_2 = SIGMA_2).to(DEVICE)

    #Declare the optimizer
    #optimizer = optim.SGD(net.parameters(),lr=1e-4,momentum=0.9) #
    optimizer = optim.Adam(net.parameters())

    for epoch in range(TRAIN_EPOCHS):
        train(net, optimizer,data=train_x,target=train_y,NUM_BATCHES=NUM_BATCHES)

    print('Training Ends!')

    return net

def test(net, colors_pokemon, pokemonType, TEST_SAMPLES):
    results = {}
    for color in colors_pokemon:
        r,g,b = colors.to_rgb(color)
        temp = torch.tensor(np.asarray([r,g,b]).astype(np.float32))
        outputs = np.zeros(100)
        for i in range(TEST_SAMPLES):
            output = net.forward(temp)
            output = output.max(1, keepdim=True)[1].data.numpy()
            outputs[i] = output[0][0]
        outputs = pd.DataFrame(outputs)
        outputs = outputs[0].value_counts()
        outputs = pd.DataFrame(outputs)
        outputs['Type'] = outputs.index.values.astype(np.int)
        outputs['Count'] = outputs[0]
        outputs = outputs.drop([0],axis=1)
        outputs = outputs.replace({'Type': pokemonType})
        #results[color] = { 'RGB': [r,g,b],'Type': outputs.to_json(orient='values')}
        results[color] = outputs.to_json(orient='values')
    
    return results


TRAIN_EPOCHS = 5
TEST_SAMPLES = 100
NUM_BATCHES = 10
#https://www.rapidtables.com/web/color/RGB_Color.html#color-table
newColors = ['Orange','Lime','Maroon','Silver','Navy','Magenta','Aqua','Gold','Chocolate','Olive']

print('Generating Data set.',)

train_x,train_y,pokemonType, pokemonColors = generatePokemonData(NUM_BATCHES)
net = trainBBB(train_x,train_y,TRAIN_EPOCHS,NUM_BATCHES)

results = {}
results['original'] = test(net, pokemonColors, pokemonType, TEST_SAMPLES)
results['newData'] = test(net, newColors, pokemonType, TEST_SAMPLES)

with open('PokemonResults.json', 'w') as fp:
        json.dump(results, fp, indent=4, sort_keys=True)