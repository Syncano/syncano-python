# Syncano v4.0

## Usage examples

### Authentication

```python
import syncano
connection = syncano.connect(email='', password='')
```


### Accessing models
Each model is generated based on API schema and is available **after** connection initialization.

```python
Instance = connection.models.Instance
```


### Queries

```python
# Get all instances
Instance.please.list()
Instance.please.all()

# Get only two instances
Instance.please.limit(2).list()

# Get raw JSON
Instance.please.raw().list()

# Get instance named syncano
Instance.please.get('syncano')
Instance.please.detail('syncano')

# Update instance named syncano
Instance.please.update('syncano', data={'description': 'new one'})

# Delete instance named syncano
Instance.please.delete('syncano')

# Create instance named test
Instance.please.create(name='test', description='test')
```


### Model instance methods

```python
# Create
instance = Instance(name='syncano', description='test')
instance.save()

instance = Instance()
instance.name = 'syncano'
instance.description = 'test'
instance.save()

# Update
instance.description = 'new one'
instance.save()

# Delete
instance.delete()
```


### Related models
Based on HATEOAS links attached to each model ORM is creating relations to all of them.

```python
instance = Instance.please.get('syncano')
instance.admins
instance.admins.raw()
instance.admins.create()
instance.admins.delete(4)
```
