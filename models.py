
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal

class DDPG_Critic(nn.Module):
    def __init__(self, state_size, action_size, hidden_dims=(64,64), seed = 0):
        super(DDPG_Critic, self).__init__()
        self.seed = torch.manual_seed(seed)
        # ARCHITECTURE
        self.input_layer = nn.Linear(state_size, hidden_dims[0])
        self.hidden_layers = nn.ModuleList()
        for i in range(len(hidden_dims)-1):
            in_dim = hidden_dims[i]
            if i == 0:
                in_dim += action_size # append actions to the first hidden layer
            hidden_layer = nn.Linear(in_dim, hidden_dims[i+1])
            self.hidden_layers.append(hidden_layer)
        self.output_layer = nn.Linear(hidden_dims[-1], 1) #Critic only has one Q(s,a)
        # ACTIVATION FUNCTIONS
        self.activation_fc = F.relu # all the layers except output
        # SET DEVICE
        device = "cpu"
        if torch.cuda.is_available():
            device = "cuda:0"
        self.device = torch.device(device)
        self.to(self.device)

    def _format(self, state, action):
        x, y = state, action
        if not isinstance(x, torch.Tensor):
            x = torch.tensor(x, device=self.device, dtype=torch.float32)
            x = x.unsqueeze(0)
        if not isinstance(y, torch.Tensor):
            y = torch.tensor(y, device=self.device, dtype=torch.float32)
            y = y.unsqueeze(0)
        return x, y

    def forward(self, state, action):
        x, y = self._format(state, action)
        x = self.activation_fc(self.input_layer(x))
        for i, hidden_layer in enumerate(self.hidden_layers):
            if i == 0:
                x = torch.cat((x, y), dim=1)
            x = self.activation_fc(hidden_layer(x))
        return self.output_layer(x)


class DDPG_Actor(nn.Module):
    def __init__(self, state_size, action_size=4, action_bounds=(-1,1), hidden_dims=(64,64), seed=0):
        super(DDPG_Actor, self).__init__()
        self.seed = torch.manual_seed(seed)
        # ARCHITECTURE
        self.input_layer = nn.Linear(state_size, hidden_dims[0])
        self.hidden_layers = nn.ModuleList()
        for i in range(len(hidden_dims)-1):
            hidden_layer = nn.Linear(hidden_dims[i], hidden_dims[i+1])
            self.hidden_layers.append(hidden_layer)
        self.output_layer = nn.Linear(hidden_dims[-1], action_size)
        # ACTIVATION FUNCTIONS
        self.activation_fc = F.relu
        self.out_activation_fc = F.tanh
        # SET DEVICE
        device = "cpu"
        if torch.cuda.is_available():
            device = "cuda:0"
        self.device = torch.device(device)
        self.to(self.device)

        # IN CASE ACTION BOUNDS DO NOT CASE WITH OUR ACTIVATION FUNCTION LIMITS
        self.env_min, self.env_max = action_bounds
        self.env_min = torch.tensor(self.env_min, device=self.device, dtype=torch.float32)
        self.env_max = torch.tensor(self.env_max, device=self.device, dtype=torch.float32)
        self.nn_min = self.out_activation_fc(torch.Tensor([float('-inf')])).to(self.device)
        self.nn_max = self.out_activation_fc(torch.Tensor([float('inf')])).to(self.device)
        self.rescale_fn = lambda x: (x - self.nn_min) * (self.env_max - self.env_min) / (self.nn_max - self.nn_min) + self.env_min

    def _format(self, state):
        x = state
        if not isinstance(x, torch.Tensor):
            x = torch.tensor(x, device=self.device, dtype=torch.float32)
            x = x.unsqueeze(0)
        return x

    def forward(self, state):
        x = self._format(state)
        x = self.activation_fc(self.input_layer(x))
        for hidden_layer in self.hidden_layers:
            x = self.activation_fc(hidden_layer(x))
        x = self.output_layer(x)
        x = self.out_activation_fc(x)
        return x
        #return self.rescale_fn(x) #not necessary to rescale in this case
