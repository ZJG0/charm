'''
Brent Waters (Pairing-based)
 
| From: "Ciphertext-Policy Attribute-Based Encryption: An Expressive, Efficient, and Provably Secure Realization", Appendix C.
| Published in: 2008
| Available from: http://eprint.iacr.org/2008/290.pdf
| Notes: Security Assumption: parallel q-DBDHE. The sole disadvantage of this scheme is the high number of pairings
| that must be computed during the decryption process (2 + N) for N attributes mathing in the key.

* type:            ciphertext-policy attribute-based encryption (public key)
* setting:        Pairing

:Authors:    J Ayo Akinyele
:Date:            11/2010
'''
from charm.toolbox.pairinggroup import *
from charm.toolbox.secretutil import *
from charm.toolbox.ABEnc import *

debug = False
class CPabe09(ABEnc):
    """
    >>> from schemes.example_values import pairing_SS512_val as msg
    >>> group = PairingGroup('SS512')
    >>> cpabe = CPabe09(groupObj)
    >>> (master_secret_key, public_key) = cpabe.setup()
    >>> policy = '((ONE or THREE) and (TWO or FOUR))'
    >>> attr_list = ['THREE', 'ONE', 'TWO']
    >>> secret_key = cpabe.keygen(public_key, master_secret_key, attr_list)
    >>> cipher_text = cpabe.encrypt(public_key, msg, policy)
    >>> cpabe.decrypt(public_key, secret_key, cipher)
    [8498626471746535541889196006969623245883442038940767658411896849230802260262151353691177896167637279292812138807029583456775233580306113979341887791855557, 6966939460945789223279096602928312619651295009575045207502056308294974480025386597816838423778648241850303711370830167285562786901756561121522858944449876]
    """
    
    def __init__(self, groupObj):
        ABEnc.__init__(self)
        global util, group
        util = SecretUtil(groupObj, groupObj._verbose)        
        group = groupObj
                        
    def setup(self):
        g1, g2 = group.random(G1), group.random(G2)
        alpha, a = group.random(), group.random()        
        e_gg_alpha = pair(g1,g2) ** alpha
        msk = {'g1^alpha':g1 ** alpha, 'g2^alpha':g2 ** alpha}        
        pk = {'g1':g1, 'g2':g2, 'e(gg)^alpha':e_gg_alpha, 'g1^a':g1 ** a, 'g2^a':g2 ** a}
        return (msk, pk)
    
    def keygen(self, pk, msk, attributes):        
        t = group.random()
        K = msk['g2^alpha'] * (pk['g2^a'] ** t)
        L = pk['g2'] ** t
        k_x = [group.hash(s, G1) ** t for s in attributes]
        
        K_x = {}
        for i in range(0, len(k_x)):
            K_x[ attributes[i] ] = k_x[i]    

        key = { 'K':K, 'L':L, 'K_x':K_x, 'attributes':attributes }
        return key
    
    def encrypt(self, pk, M, policy_str):
        # Extract the attributes as a list
        policy = util.createPolicy(policy_str)        
        p_list = util.getAttributeList(policy)
        s = group.random()
        C_tilde = (pk['e(gg)^alpha'] ** s) * M
        C_0 = pk['g1'] ** s
        C, D = {}, {}
        secret = s
        shares = util.calculateSharesList(secret, policy)

        # ciphertext
        for i in range(len(p_list)):
            r = group.random()
            if shares[i][0] == p_list[i]:
               attr = shares[i][0].getAttribute() 
               C[ p_list[i] ] = ((pk['g1^a'] ** shares[i][1]) * (group.hash(attr, G1) ** -r))
               D[ p_list[i] ] = (pk['g2'] ** r)
        
        if debug: print("SessionKey: %s" % C_tilde)
        return { 'C0':C_0, 'C':C, 'D':D , 'C_tilde':C_tilde, 'policy':policy_str, 'attribute':p_list }
    
    def decrypt(self, pk, sk, ct):
        policy = util.createPolicy(ct['policy'])
        pruned = util.prune(policy, sk['attributes'])
        if pruned == False:
            return False
        coeffs = util.getCoefficients(policy)
        numerator = pair(ct['C0'], sk['K'])
        
        # create list for attributes in order...
        k_x, w_i = {}, {}
        for i in pruned:
            j = i.getAttributeAndIndex()
            k = i.getAttribute()
            k_x[ j ] = sk['K_x'][k]
            w_i[ j ] = coeffs[j]
            #print('Attribute %s: coeff=%s, k_x=%s' % (j, w_i[j], k_x[j]))
            
        C, D = ct['C'], ct['D']
        denominator = group.init(GT, 1)
        for i in pruned:
            j = i.getAttributeAndIndex()
            denominator *= ( pair(C[j] ** w_i[j], sk['L']) * pair(k_x[j] ** w_i[j], D[j]) )   
        return ct['C_tilde'] / (numerator / denominator)

