import torch
import torch.nn as nn
import torch.nn.functional as F

from goggles.utils.functional import pairwise_squared_euclidean_distances


def my_loss_function(reconstructed_x, z_patches, prototypes, padding_idx, x, lambda_=0.01):
    """
        reconstructed_x : batch_size, channels, height, width
        z_patches       : batch_size, num_patches, embedding_dim
        prototypes      : batch_size, num_prototypes, embedding_dim
        padding_idx     : batch_size
        x               : batch_size, channels, height, width
    """
    assert not x.requires_grad

    batch_size = x.size(0)

    loss = F.mse_loss(reconstructed_x, x, size_average=False)
    for i in range(batch_size):
        image_patches = z_patches[i]
        image_prototypes = prototypes[i][:padding_idx[i]]

        dists = pairwise_squared_euclidean_distances(
            image_prototypes, image_patches)
        min_dists = torch.min(dists, dim=1)[0]

        prototype_loss = torch.sum(min_dists)
        loss = loss + (lambda_ * prototype_loss)

    loss = loss / batch_size
    return loss


class CustomLoss(object):
    def __init__(self, lambda_val=0.001):
        super(CustomLoss, self).__init__()

        self._lambda_val = lambda_val
        self._reconstruction_loss = F.mse_loss
        self._xentropy_loss = nn.CrossEntropyLoss()

    def __call__(self, reconstructed_x, z_patches, prototypes, padding_idx, x):
        """
            reconstructed_x : batch_size, channels, height, width
            z_patches       : batch_size, num_patches, embedding_dim
            prototypes      : batch_size, num_prototypes, embedding_dim
            padding_idx     : batch_size
            x               : batch_size, channels, height, width
        """
        assert not x.requires_grad

        lambda_val = self._lambda_val
        batch_size = x.size(0)

        loss = lambda_val * self._reconstruction_loss(
            reconstructed_x, x, size_average=False)

        for i in range(batch_size):
            image_patches = z_patches[i]
            associated_prototypes = prototypes[i][:padding_idx[i]]

            dists = pairwise_squared_euclidean_distances(
                associated_prototypes, image_patches)
            nearest_patch_idxs = torch.min(dists, dim=1)[1]

            loss += self._xentropy_loss(-dists, nearest_patch_idxs)

        loss = loss / batch_size
        return loss

    def cuda(self, device=None):
        self._xentropy_loss = \
            self._xentropy_loss.cuda(device)


if __name__ == '__main__':
    reconstructed_x = torch.autograd.Variable(torch.rand(4, 3, 64, 64))
    z_patches = torch.autograd.Variable(torch.rand(4, 64, 512))
    attribute_prototypes = torch.autograd.Variable(torch.rand(4, 37, 512))
    padding_idx = torch.IntTensor([4, 5, 9, 37])
    x = torch.autograd.Variable(torch.rand(4, 3, 64, 64))

    print(my_loss_function(reconstructed_x, z_patches, attribute_prototypes, padding_idx, x))

    # attr = torch.IntTensor([
    #     [1, 2, 3, 4, 0, 0, 0],
    #     [1, 2, 0, 0, 0, 0, 0],
    #     [1, 2, 3, 4, 5, 6, 7]
    # ])
    #
    # print(attr.nonzero())
