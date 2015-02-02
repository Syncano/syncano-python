# Syncano v4.0

## Usage examples

### Authentication

```python
import syncano

# via email & password
connection = syncano.connect(email='', password='')

# via API key
connection = syncano.connect(api_key='')
```


### Accessing models / endpoints
Each model is generated based on API schema and is available **after** connection initialization.

```python
Instance = connection.Instance
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

The same queries can be done via connection:

```python
# Get all instances
connection.instances.list()
connection.instances.all()

# Get only two instances
connection.instances.limit(2).list()

# Get raw JSON
connection.instances.raw().list()
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

### Relations

`CodeBoxExecutionTrace` is related to `instance`, `codebox` and `codebox_schedule` so model should have few aditional fields:

```python
codebox = CodeBoxExecutionTrace()
codebox.instance_name = 'syncano'
codebox.codebox_id = 1
codebox.schedule_id = 2
codebox.save()
```

### Connection juggling


```python
connection = syncano.connect(email='', password='')
second_connection = syncano.connect(email='', password='')

# ORM
instances = connection.insatcnes.using(second_connection).list()

# Model instance
insatnce = Instance()
instance.name = 'test'
insatcne.save(connection=second_connection)

```
