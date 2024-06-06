import torch

import torch_geometric.typing
from torch_geometric.nn import SGConv
from torch_geometric.testing import is_full_test
from torch_geometric.typing import SparseTensor
from torch_geometric.utils import to_torch_csc_tensor
from torch_geometric.nn.dense.linear import Linear

import pdb
import pytest

import pytest

def test_sg_conv():
    x = torch.randn(4, 16)
    edge_index = torch.tensor([[0, 0, 0, 1, 2, 3], [1, 2, 3, 0, 0, 0]])
    value = torch.rand(edge_index.size(1))
    adj1 = to_torch_csc_tensor(edge_index, size=(4, 4))
    adj2 = to_torch_csc_tensor(edge_index, value, size=(4, 4))

    conv = SGConv(16, 32, K=10)
    assert str(conv) == 'SGConv(16, 32, K=10)'

    out1 = conv(x, edge_index)
    assert out1.size() == (4, 32)
    assert torch.allclose(conv(x, adj1.t()), out1, atol=1e-6)

    out2 = conv(x, edge_index, value)
    assert out2.size() == (4, 32)
    assert torch.allclose(conv(x, adj2.t()), out2, atol=1e-6)

    if torch_geometric.typing.WITH_TORCH_SPARSE:
        adj3 = SparseTensor.from_edge_index(edge_index, sparse_sizes=(4, 4))
        adj4 = SparseTensor.from_edge_index(edge_index, value, (4, 4))
        assert torch.allclose(conv(x, adj4.t()), out2, atol=1e-6)
        assert torch.allclose(conv(x, adj3.t()), out1, atol=1e-6)

    if is_full_test():
        jit = torch.jit.script(conv)
        assert torch.allclose(jit(x, edge_index), out1, atol=1e-6)
        assert torch.allclose(jit(x, edge_index, value), out2, atol=1e-6)

        if torch_geometric.typing.WITH_TORCH_SPARSE:
            assert torch.allclose(jit(x, adj3.t()), out1, atol=1e-6)
            assert torch.allclose(jit(x, adj4.t()), out2, atol=1e-6)

    conv.cached = True
    conv(x, edge_index)
    assert conv._cached_x is not None
    assert torch.allclose(conv(x, edge_index), out1, atol=1e-6)
    assert torch.allclose(conv(x, adj1.t()), out1, atol=1e-6)
    if torch_geometric.typing.WITH_TORCH_SPARSE:
        assert torch.allclose(conv(x, adj3.t()), out1, atol=1e-6)

def test_sg_conv_pure():
    in_channels=16
    out_channels=32
    K=10

    x = torch.randn(4, 16)

    torch.manual_seed(42)

    edge_index = torch.tensor([[0, 0, 0, 1, 2, 3], [1, 2, 3, 0, 0, 0]])
    conv = SGConv(in_channels, in_channels, K=K, apply_linearity=False)

    ext_lin = Linear(in_channels, out_channels)
    ext_lin.reset_parameters()

    #reset the seed to ensure same init for torch.nn.Linear vs SGConv internal linearity
    torch.manual_seed(42)

    conv_lin = SGConv(in_channels, out_channels, K=K, apply_linearity=True)


    y = ext_lin(conv(x, edge_index))
    y2 = conv_lin(x, edge_index)

    assert torch.allclose(y, y2)

    with pytest.raises(AssertionError, match="SGConv with apply_linearity=False does not support differet in and out channels."):
        conv = SGConv(in_channels, out_channels, K=K, apply_linearity=False)
