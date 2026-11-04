import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Product, ProductVariant } from '../types';
import { Plus, Edit2, Trash2, RefreshCw, CheckCircle, Package, Layers, Tag, Image as ImageIcon } from 'lucide-react';

export const CatalogPage: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [reindexing, setReindexing] = useState(false);
  const [reindexStatus, setReindexStatus] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [basePrice, setBasePrice] = useState(850);
  const [imageUrl, setImageUrl] = useState('');

  // Variant Form state for modal
  const [variants, setVariants] = useState<{ sku: string; title: string; price: number; stock: number; size?: string; color?: string }[]>([
    { sku: 'SKU-01', title: 'Standard', price: 850, stock: 20, size: 'M', color: 'Black' }
  ]);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const data = await apiClient.catalog.getProducts();
      setProducts(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const handleReindex = async () => {
    setReindexing(true);
    setReindexStatus(null);
    try {
      const res = await apiClient.kb.reindex();
      setReindexStatus(`Knowledge reindexed! ${res.chunks_indexed} chunks embedded into pgvector.`);
      setTimeout(() => setReindexStatus(null), 4000);
    } catch (err) {
      setReindexStatus('Reindexing failed. Check backend logs.');
    } finally {
      setReindexing(false);
    }
  };

  const openCreateModal = () => {
    setEditingProduct(null);
    setTitle('');
    setDescription('');
    setCategory("Men's Fashion");
    setBasePrice(850);
    setImageUrl('https://images.unsplash.com/photo-1581655353564-df123a1eb820?w=600&auto=format&fit=crop&q=80');
    setVariants([{ sku: `SKU-${Date.now().toString().slice(-4)}`, title: 'Standard', price: 850, stock: 20, size: 'L', color: 'Black' }]);
    setIsModalOpen(true);
  };

  const openEditModal = (p: Product) => {
    setEditingProduct(p);
    setTitle(p.title);
    setDescription(p.description || '');
    setCategory(p.category || '');
    setBasePrice(p.base_price);
    setImageUrl(p.image_url || '');
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this product?')) {
      await apiClient.catalog.deleteProduct(id);
      fetchProducts();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editingProduct) {
      await apiClient.catalog.updateProduct(editingProduct.id, {
        title,
        description,
        category,
        base_price: basePrice,
        image_url: imageUrl,
      });
    } else {
      await apiClient.catalog.createProduct({
        title,
        description,
        category,
        base_price: basePrice,
        image_url: imageUrl,
        variants: variants as any,
      });
    }
    setIsModalOpen(false);
    fetchProducts();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Product Catalog</h1>
          <p className="text-sm text-slate-500 mt-1">Manage e-commerce products, variants, SKU inventory, and AI grounding data.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleReindex}
            disabled={reindexing}
            className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-xl text-sm transition-all shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${reindexing ? 'animate-spin' : ''}`} />
            <span>{reindexing ? 'Embedding into pgvector...' : 'Reindex Knowledge'}</span>
          </button>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-xl text-sm transition-all shadow-sm shadow-blue-500/20"
          >
            <Plus className="w-4 h-4" />
            <span>Add Product</span>
          </button>
        </div>
      </div>

      {reindexStatus && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2.5">
          <CheckCircle className="w-5 h-5 text-emerald-600" />
          <span>{reindexStatus}</span>
        </div>
      )}

      {/* Product List Cards */}
      {loading ? (
        <div className="py-24 text-center text-slate-400">Loading catalog items...</div>
      ) : products.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center">
          <Package className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No products found</h3>
          <p className="text-sm text-slate-500 mt-1">Click "Add Product" above to create your first catalog item.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map((p) => {
            const totalStock = p.variants?.reduce((acc, v) => acc + (v.stock || 0), 0) ?? 0;
            return (
              <div key={p.id} className="bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col">
                <div className="h-48 w-full bg-slate-100 relative overflow-hidden">
                  {p.image_url ? (
                    <img src={p.image_url} alt={p.title} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-300">
                      <ImageIcon className="w-12 h-12" />
                    </div>
                  )}
                  <span className="absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold bg-white/90 backdrop-blur text-slate-800 shadow-sm">
                    {p.category || 'General'}
                  </span>
                  <span className={`absolute top-3 right-3 px-2.5 py-1 rounded-full text-xs font-semibold shadow-sm ${
                    totalStock > 0 ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
                  }`}>
                    {totalStock > 0 ? `${totalStock} In Stock` : 'Out of Stock'}
                  </span>
                </div>

                <div className="p-5 flex-1 flex flex-col justify-between">
                  <div>
                    <h3 className="text-base font-bold text-slate-900 leading-snug">{p.title}</h3>
                    <p className="text-xs text-slate-500 line-clamp-2 mt-1.5">{p.description}</p>
                    <div className="mt-3 text-lg font-bold text-blue-600">৳ {p.base_price}</div>

                    {/* Variants list preview */}
                    <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5">
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Variants ({p.variants?.length || 0})</div>
                      <div className="flex flex-wrap gap-1.5">
                        {p.variants?.map((v) => (
                          <span key={v.id} className="px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-[11px] text-slate-700 font-mono">
                            {v.sku}: ৳{v.price} ({v.stock} in stock)
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
                    <button
                      onClick={() => openEditModal(p)}
                      className="p-2 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors text-xs flex items-center gap-1"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      <span>Edit</span>
                    </button>
                    <button
                      onClick={() => handleDelete(p.id)}
                      className="p-2 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors text-xs flex items-center gap-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Delete</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold text-slate-900 mb-4">
              {editingProduct ? 'Edit Product' : 'Add New Product'}
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Product Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500"
                  placeholder="e.g. Premium Cotton Polo Shirt"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Category</label>
                  <input
                    type="text"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500"
                    placeholder="Men's Fashion"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Base Price (৳)</label>
                  <input
                    type="number"
                    required
                    value={basePrice}
                    onChange={(e) => setBasePrice(parseFloat(e.target.value) || 0)}
                    className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Image URL</label>
                <input
                  type="url"
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500"
                  placeholder="https://..."
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:border-blue-500"
                  placeholder="Fabric composition, dimensions, care instructions..."
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold shadow-sm"
                >
                  {editingProduct ? 'Save Changes' : 'Create Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
