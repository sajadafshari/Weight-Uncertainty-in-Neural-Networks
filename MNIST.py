from BayesBackpropagation import *

from torch.utils.data.dataloader import DataLoader

from data.parser import parse_mnist
from data.dataset import MNISTDataset
from data.transforms import MNISTTransform

class MNIST(object):
    def __init__(self,BATCH_SIZE,TEST_BATCH_SIZE,CLASSES,TRAIN_EPOCHS,SAMPLES,TEST_SAMPLES,hasScalarMixturePrior,PI,SIGMA_1,SIGMA_2,INPUT_SIZE,LAYERS,ACTIVATION_FUNCTIONS,LR=1e-4,PARSE_SEED=1,MODE='mlp'):
        #Prepare data
        if MODE == 'mlp':
            train_data, train_label, valid_data, valid_label, test_data, test_label = parse_mnist(2, 'data/', 10000, PARSE_SEED)
        elif cfg.mode == 'cnn':
            train_data, train_label, valid_data, valid_label, test_data, test_label = parse_mnist(4, 'data/', 10000, PARSE_SEED)
        else:
            raise ValueError('Not supported mode')

        transform = MNISTTransform()
        train_dataset = MNISTDataset(train_data, train_label, transform=transform)
        valid_dataset = MNISTDataset(valid_data, valid_label, transform=transform)
        test_dataset = MNISTDataset(test_data, test_label, transform=transform)
        self.train_loader = DataLoader(train_dataset, BATCH_SIZE, shuffle=True, **LOADER_KWARGS)
        self.valid_loader = DataLoader(valid_dataset, TEST_BATCH_SIZE, shuffle=False, **LOADER_KWARGS)
        self.test_loader = DataLoader(test_dataset, TEST_BATCH_SIZE, shuffle=False, **LOADER_KWARGS)

        #Hyper parameter setting
        self.TEST_BATCH_SIZE = TEST_BATCH_SIZE
        self.TRAIN_SIZE = len(self.train_loader.dataset)
        self.TEST_SIZE = len(self.test_loader.dataset)
        self.NUM_BATCHES = len(self.train_loader)
        self.NUM_TEST_BATCHES = len(self.test_loader)

        self.CLASSES = CLASSES
        self.TRAIN_EPOCHS = TRAIN_EPOCHS
        self.SAMPLES = SAMPLES
        self.TEST_SAMPLES = TEST_SAMPLES

        #Checking if the mentioned batch sizes are feasible
        assert (self.TRAIN_SIZE % BATCH_SIZE) == 0
        assert (self.TEST_SIZE % TEST_BATCH_SIZE) == 0

        #Network Declaration
        self.net = BayesianNetwork(inputSize = INPUT_SIZE,\
                      CLASSES = CLASSES, \
                      layers=LAYERS, \
                      activations = ACTIVATION_FUNCTIONS, \
                      SAMPLES = SAMPLES, \
                      BATCH_SIZE = BATCH_SIZE,\
                      NUM_BATCHES = self.NUM_BATCHES,\
                      hasScalarMixturePrior = hasScalarMixturePrior,\
                      PI = PI,\
                      SIGMA_1 = SIGMA_1,\
                      SIGMA_2 = SIGMA_2).to(DEVICE)

        #Optimizer declaration
        self.optimizer = optim.SGD(self.net.parameters(),lr=LR) #self.optimizer = optim.Adam(self.net.parameters())

    #Define the training step for MNIST data set
    def train(self):
        for batch_idx, (X, y) in enumerate(self.train_loader):      
            self.net.zero_grad()
            loss = self.net.BBB_loss(X, y)
            loss.backward()
            self.optimizer.step()
    
    #Testing the ensemble
    def test(self,valid=True):
        data_loader = self.valid_loader if valid else self.test_loader
        correct = 0
        with torch.no_grad():
            for data, target in data_loader:
                data, target = data.to(DEVICE), target.to(DEVICE)
                for b in range(self.TEST_SAMPLES):
                    #X = Variable(torch.Tensor(data[b * self.TEST_BATCH_SIZE: (b+1) * self.TEST_BATCH_SIZE]))  #.cuda())
                    output = self.net.forward(data, infer=True)
                    pred = output.max(1, keepdim=True)[1]
                    correct += pred.eq(target.view_as(pred)).sum().item()
        
        accuracy = correct/self.TEST_SIZE
        
        return round(100*(1 - accuracy), 3)#Error